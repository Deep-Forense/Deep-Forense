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
     fallaron (FOR-114). Capa 3 (Sprint 3): FraudScoringService (FOR-111)
     puntúa cada artifact completado y ConsolidationService (FOR-112/113)
     consolida el job según la política configurada (worst_case_dominates
     por default, weighted_average si se configura explícitamente).

Solo conoce puertos (inversión de dependencias): sin Celery, Mongo, MinIO,
OpenCV ni HTTP en este nivel.
"""
import asyncio
import hashlib
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
from app.domain.ports.pdf_structure_analyzer_port import PdfStructureAnalyzerPort
from app.domain.ports.storage_port import StoragePort
from app.domain.ports.text_cognitive_analyzer_port import TextCognitiveAnalyzerPort, TextCognitiveResult
from app.domain.services.benford_applicability_service import BenfordApplicabilityService
from app.domain.services.consolidation_service import ConsolidationService, ScoredArtifact
from app.domain.services.document_consistency_service import DocumentConsistencyService
from app.domain.services.fraud_scoring_service import FraudScoringService
from app.domain.services.image_classification_service import ImageClassificationService

logger = logging.getLogger(__name__)


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
        fraud_scoring: FraudScoringService,
        consolidation: ConsolidationService,
        image_classification: ImageClassificationService,
        document_consistency: DocumentConsistencyService | None = None,
        pdf_structure_analyzer: PdfStructureAnalyzerPort | None = None,
        document_image_concurrency: int = 2,
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
        self._fraud_scoring = fraud_scoring
        self._consolidation = consolidation
        self._image_classification = image_classification
        self._document_consistency = document_consistency or DocumentConsistencyService()
        self._pdf_structure_analyzer = pdf_structure_analyzer
        self._document_image_semaphore = asyncio.Semaphore(max(1, document_image_concurrency))

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

        # FOR-114: el job solo es FAILED si TODOS los artifacts fallaron.
        completed_pairs = [
            (artifact, analysis)
            for artifact, analysis in zip(artifacts, results)
            if analysis is not None
        ]
        job_status = "COMPLETED" if completed_pairs else "FAILED"

        # Capa 3 (FOR-111 + FOR-112/113): scoring por artifact + consolidación.
        consolidated = None
        if completed_pairs:
            scored = [
                ScoredArtifact(
                    artifact_id=artifact.artifact_id,
                    type=artifact.type,
                    fraud_score=self._fraud_scoring.score(analysis),
                    analysis_complete=(
                        analysis.cognitive_available is not False
                        and analysis.ocr_available is not False
                    ),
                )
                for artifact, analysis in completed_pairs
            ]
            consolidated = self._consolidation.consolidate(scored)

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
        return await self._analyze_text(job_id, artifact, content)

    async def _analyze_text(
        self, job_id: str, artifact: Artifact, content: bytes
    ) -> ArtifactAnalysis:
        warnings: list[str] = []
        structure = None
        if self._pdf_structure_analyzer is not None and content.startswith(b"%PDF"):
            try:
                structure = await self._pdf_structure_analyzer.analyze(content)
            except Exception as exc:
                logger.warning("Análisis estructural PDF no disponible: %s", exc)
                warnings.append("pdf_structure_unavailable")
        try:
            extraction = await self._ocr.extract_with_metadata(content)
        except Exception as exc:
            logger.warning("Extracción OCR no disponible: %s", exc)
            if structure is None:
                raise
            return ArtifactAnalysis(
                benford_applicable=False,
                pdf_structure_score=structure.score,
                pdf_structure=structure.evidence,
                pdf_structure_flags=list(structure.flags),
                ocr_available=False,
                cognitive_available=False,
                analysis_warnings=[*warnings, "ocr_unavailable", "cognitive_analysis_skipped"],
            )
        warnings.extend(extraction.warnings)
        consistency = self._document_consistency.analyze(extraction.text)
        try:
            cognitive = await self._text_analyzer.analyze(extraction.text)
            cognitive_available = True
        except Exception as exc:
            logger.warning("Análisis semántico documental no disponible: %s", exc)
            cognitive = TextCognitiveResult(document_type=None, financial_amounts=[], ai_flags=[])
            cognitive_available = False
            warnings.append("cognitive_analysis_unavailable")
        visual_evidence = await asyncio.gather(*(
            self._analyze_embedded_image(job_id, artifact, index, image)
            for index, image in enumerate(extraction.visual_images, start=1)
        ))
        hashes: dict[str, int] = {}
        for evidence, image in zip(visual_evidence, extraction.visual_images):
            digest = hashlib.sha256(image.content).hexdigest()
            if digest in hashes:
                evidence["duplicate_of"] = hashes[digest]
            else:
                hashes[digest] = evidence["index"]
        visual_flags = list(dict.fromkeys(
            flag for evidence in visual_evidence for flag in evidence.get("ai_flags", [])
        ))
        visual_scores = [
            evidence["technical_score"] for evidence in visual_evidence
            if evidence.get("technical_score") is not None
        ]
        dominant_visual = max(
            (evidence for evidence in visual_evidence if evidence.get("technical_score") is not None),
            key=lambda evidence: evidence["technical_score"], default=None,
        )

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
            ai_flags=list(dict.fromkeys([
                *cognitive.ai_flags, *consistency.flags, *visual_flags,
            ])),
            benford_applicable=applicable,
            benford_score=benford_score,
            document_page_count=extraction.page_count,
            document_analyzed_pages=extraction.analyzed_pages,
            document_text_layer_pages=extraction.text_layer_pages,
            document_ocr_pages=extraction.ocr_pages,
            document_embedded_images=extraction.embedded_images,
            document_truncated=extraction.truncated,
            document_consistency_score=consistency.score,
            document_consistency_checks=consistency.checks,
            document_visual_score=max(visual_scores) if visual_scores else None,
            document_visual_evidence=visual_evidence,
            document_visual_heatmap_ref=(
                dominant_visual.get("heatmap_ref") if dominant_visual else None
            ),
            pdf_structure_score=structure.score if structure else None,
            pdf_structure=structure.evidence if structure else None,
            pdf_structure_flags=list(structure.flags) if structure else [],
            ocr_available=not bool(extraction.warnings),
            cognitive_available=cognitive_available,
            analysis_warnings=warnings,
        )

    async def _analyze_embedded_image(self, job_id, artifact, index, image) -> dict:
        """Analiza una imagen original del PDF; Gemini es opcional y nunca tumba el PDF."""
        exif_result, ela_result, cognitive_result = await asyncio.gather(
            self._exif_analyzer.analyze(image.content),
            self._ela_analyzer.analyze(image.content),
            self._analyze_embedded_image_cognitive(image.content),
            return_exceptions=True,
        )
        exif_score = None if isinstance(exif_result, Exception) else exif_result
        ela_score = None if isinstance(ela_result, Exception) else ela_result.score
        heatmap_ref = None
        if not isinstance(ela_result, Exception):
            heatmap_ref = await self._storage.save(
                path=(f"jobs/{job_id}/artifacts/{artifact.artifact_id}/"
                      f"document_image_{index}_ela.png"),
                content=ela_result.heatmap_png,
            )

        dct_score = None
        if self._benford_applicability.applies_to_image(image.content):
            try:
                coefficients = await self._dct_analyzer.extract_coefficients(image.content)
                dct_score = await self._benford_analyzer.score(coefficients)
            except Exception:
                logger.exception("DCT no disponible para imagen embebida %s", index)

        if isinstance(cognitive_result, Exception):
            logger.warning("IA visual no disponible para imagen embebida %s: %s", index, cognitive_result)
            cognitive_flags = []
            cognitive_available = False
        else:
            cognitive_flags = list(cognitive_result)
            cognitive_available = True

        scores = [score for score in (exif_score, ela_score, dct_score) if score is not None]
        aspect = image.width / max(image.height, 1)
        if aspect >= 2.5 and image.height <= 500:
            role = "SIGNATURE_CANDIDATE"
        elif 0.75 <= aspect <= 1.33 and max(image.width, image.height) <= 800:
            role = "SEAL_OR_LOGO_CANDIDATE"
        elif max(image.width, image.height) <= 600:
            role = "GRAPHIC"
        else:
            role = "PHOTO_OR_SCAN"
        return {
            "index": index, "page": image.page_number, "width": image.width,
            "height": image.height, "role": role,
            "exif_score": exif_score, "ela_score": ela_score,
            "dct_benford_score": dct_score,
            "technical_score": round(sum(scores) / len(scores), 4) if scores else None,
            "ai_flags": cognitive_flags, "cognitive_available": cognitive_available,
            "heatmap_ref": heatmap_ref,
        }

    async def _analyze_embedded_image_cognitive(self, content: bytes) -> list:
        async with self._document_image_semaphore:
            return await self._image_analyzer.analyze(content)

    async def _analyze_image(
        self, job_id: str, artifact: Artifact, content: bytes
    ) -> ArtifactAnalysis:
        exif_score = await self._exif_analyzer.analyze(content)

        ela_result = await self._ela_analyzer.analyze(content)
        ela_heatmap_ref = await self._storage.save(
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

        try:
            gemini_flags = await self._image_analyzer.analyze(content)
            cognitive_available = True
            image_classification, classification_message = self._image_classification.classify(
                gemini_flags, exif_score, ela_result.score
            )
            warnings = []
        except Exception as exc:
            logger.warning("IA visual no disponible; se conservan señales técnicas: %s", exc)
            gemini_flags = []
            cognitive_available = False
            image_classification = "INCONCLUSIVE"
            classification_message = "La IA visual no estuvo disponible; el resultado conserva EXIF, ELA y DCT."
            warnings = ["cognitive_analysis_unavailable"]

        return ArtifactAnalysis(
            ai_flags=list(gemini_flags),
            benford_applicable=applicable,
            exif_score=exif_score,
            ela_score=ela_result.score,
            dct_benford_score=dct_benford_score,
            gemini_flags=list(gemini_flags),
            image_classification=image_classification,
            image_classification_message=classification_message,
            ela_heatmap_ref=ela_heatmap_ref,
            cognitive_available=cognitive_available,
            analysis_warnings=warnings,
        )

