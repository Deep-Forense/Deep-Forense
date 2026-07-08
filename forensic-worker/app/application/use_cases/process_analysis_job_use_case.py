"""Caso de uso: ProcessAnalysisJobUseCase (Capa 2, Sprint 2).

Orquesta el pipeline forense de un job completo:

  1. Carga el job y lo marca PROCESSING (idempotente ante reintentos de Celery).
  2. Procesa cada artifact EN PARALELO (T2.M8, asyncio.gather). Un artifact
     que lanza excepción se marca FAILED sin detener a los demás.
  3. TEXT:  OcrPort -> TextCognitiveAnalyzerPort -> BenfordApplicabilityService
            -> (si aplica) BenfordAnalyzerPort sobre financial_amounts.
     IMAGE: ExifAnalyzerPort + ElaAnalyzerPort (heatmap a MinIO) +
            (si JPEG) DctAnalyzerPort -> BenfordAnalyzerPort +
            ImageCognitiveAnalyzerPort (gemini_flags).
  4. Job COMPLETED si al menos 1 artifact completó; FAILED solo si TODOS
     fallaron. El `consolidated` es un placeholder simple de Sprint 2:
     la consolidación real (FraudScoringService + ConsolidationService con
     worst_case_dominates) es Sprint 3 (FOR-112/T3.M4) — NO tocar aquí.

Solo conoce puertos (inversión de dependencias): sin Celery, Mongo, MinIO,
OpenCV ni HTTP en este nivel.
"""
import asyncio
import logging
from typing import Optional

from app.domain.entities.artifact import Artifact
from app.domain.entities.artifact_analysis import ArtifactAnalysis
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort
from app.domain.ports.benford_analyzer_port import BenfordAnalyzerPort
from app.domain.ports.dct_analyzer_port import DctAnalyzerPort
from app.domain.ports.ela_analyzer_port import ElaAnalyzerPort
from app.domain.ports.exif_analyzer_port import ExifAnalyzerPort
from app.domain.ports.image_cognitive_analyzer_port import ImageCognitiveAnalyzerPort
from app.domain.ports.ocr_port import OcrPort
from app.domain.ports.storage_port import StoragePort
from app.domain.ports.text_cognitive_analyzer_port import TextCognitiveAnalyzerPort
from app.domain.services.benford_applicability_service import BenfordApplicabilityService

logger = logging.getLogger(__name__)

# Umbrales del veredicto placeholder (mismos del mock de Sprint 1; la política
# real worst_case_dominates llega en Sprint 3 / T3.M4).
_VERDICT_APPROVED_BELOW = 0.4
_VERDICT_REJECTED_ABOVE = 0.7
_PLACEHOLDER_POLICY = "sprint2_placeholder_average"


def _placeholder_verdict(fraud_score: float) -> str:
    if fraud_score < _VERDICT_APPROVED_BELOW:
        return "APPROVED"
    if fraud_score > _VERDICT_REJECTED_ABOVE:
        return "REJECTED"
    return "SUSPICIOUS"


class ProcessAnalysisJobUseCase:
    def __init__(
        self,
        repository: AnalysisJobRepositoryPort,
        storage: StoragePort,
        exif_analyzer: ExifAnalyzerPort,
        ela_analyzer: ElaAnalyzerPort,
        dct_analyzer: DctAnalyzerPort,
        benford_analyzer: BenfordAnalyzerPort,
        ocr: OcrPort,
        text_analyzer: TextCognitiveAnalyzerPort,
        image_analyzer: ImageCognitiveAnalyzerPort,
        benford_applicability: BenfordApplicabilityService,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._exif_analyzer = exif_analyzer
        self._ela_analyzer = ela_analyzer
        self._dct_analyzer = dct_analyzer
        self._benford_analyzer = benford_analyzer
        self._ocr = ocr
        self._text_analyzer = text_analyzer
        self._image_analyzer = image_analyzer
        self._benford_applicability = benford_applicability

    async def execute(self, job_id: str) -> dict:
        status = await self._repository.get_job_status(job_id)
        if status is None:
            return {"job_id": job_id, "status": "JOB_NOT_FOUND"}
        if status not in ("PENDING", "PROCESSING"):
            # Ya procesado (idempotencia ante reintentos de Celery).
            return {"job_id": job_id, "status": status}

        await self._repository.mark_processing(job_id)
        artifacts = await self._repository.get_artifacts(job_id)

        # T2.M8: cada artifact en paralelo; la excepción de uno no detiene al resto.
        results = await asyncio.gather(
            *(self._process_artifact_safe(job_id, artifact) for artifact in artifacts)
        )

        completed = [analysis for analysis in results if analysis is not None]
        job_status = "COMPLETED" if completed else "FAILED"
        consolidated = self._placeholder_consolidated(artifacts, results) if completed else None

        await self._repository.complete_job(job_id, job_status, consolidated)
        return {"job_id": job_id, "status": job_status, "consolidated": consolidated}

    async def _process_artifact_safe(
        self, job_id: str, artifact: Artifact
    ) -> Optional[ArtifactAnalysis]:
        """Devuelve el analysis si completó, None si el artifact falló."""
        try:
            analysis = await self._process_artifact(job_id, artifact)
        except Exception:
            logger.exception(
                "Artifact %s del job %s falló; los demás continúan", artifact.artifact_id, job_id
            )
            artifact.status = "FAILED"
            await self._repository.save_artifact_result(job_id, artifact, None)
            return None

        artifact.status = "COMPLETED"
        await self._repository.save_artifact_result(job_id, artifact, analysis)
        return analysis

    async def _process_artifact(self, job_id: str, artifact: Artifact) -> ArtifactAnalysis:
        content = await self._storage.get(artifact.storage_ref)
        if artifact.is_image():
            return await self._analyze_image(job_id, artifact, content)
        return await self._analyze_text(content)

    async def _analyze_text(self, content: bytes) -> ArtifactAnalysis:
        text = await self._ocr.extract_text(content)
        cognitive = await self._text_analyzer.analyze(text)

        applicable = self._benford_applicability.applies_to_text(
            cognitive.document_type, cognitive.financial_amounts
        )
        # T2.M7: un texto no financiero NUNCA produce benford_score.
        benford_score = (
            await self._benford_analyzer.score(cognitive.financial_amounts) if applicable else None
        )

        return ArtifactAnalysis(
            document_type=cognitive.document_type,
            financial_amounts=list(cognitive.financial_amounts),
            ai_flags=list(cognitive.ai_flags),
            benford_applicable=applicable,
            benford_score=benford_score,
        )

    async def _analyze_image(
        self, job_id: str, artifact: Artifact, content: bytes
    ) -> ArtifactAnalysis:
        exif_score = await self._exif_analyzer.analyze(content)

        ela_result = await self._ela_analyzer.analyze(content)
        await self._storage.save(
            path=f"jobs/{job_id}/artifacts/{artifact.artifact_id}/ela_heatmap.png",
            content=ela_result.heatmap_png,
        )

        # T2.M3/T2.M7: DCT+Benford solo aplica a JPEG; en otros formatos la
        # señal se marca no aplicable SIN penalizar el score.
        applicable = self._benford_applicability.applies_to_image(content)
        dct_benford_score = None
        if applicable:
            coefficients = await self._dct_analyzer.extract_coefficients(content)
            dct_benford_score = await self._benford_analyzer.score(coefficients)

        gemini_flags = await self._image_analyzer.analyze(content)

        return ArtifactAnalysis(
            ai_flags=list(gemini_flags),
            benford_applicable=applicable,
            exif_score=exif_score,
            ela_score=ela_result.score,
            dct_benford_score=dct_benford_score,
            gemini_flags=list(gemini_flags),
        )

    @staticmethod
    def _placeholder_consolidated(artifacts: list, results: list) -> dict:
        """Consolidated placeholder de Sprint 2: promedio simple de las señales
        numéricas de los artifacts completados. La política real
        (worst_case_dominates) es FOR-112/T3.M4 — Sprint 3."""
        scores = [score for analysis in results if analysis is not None for score in analysis.numeric_scores()]
        fraud_score = round(sum(scores) / len(scores), 4) if scores else 0.0

        dominant = None
        best = -1.0
        for artifact, analysis in zip(artifacts, results):
            if analysis is None:
                continue
            artifact_max = max(analysis.numeric_scores(), default=0.0)
            if artifact_max > best:
                best = artifact_max
                dominant = artifact.artifact_id

        return {
            "fraud_score": fraud_score,
            "authenticity_percentage": round((1 - fraud_score) * 100),
            "risk_percentage": round(fraud_score * 100),
            "verdict": _placeholder_verdict(fraud_score),
            "dominant_artifact": dominant,
            "policy_applied": _PLACEHOLDER_POLICY,
        }
