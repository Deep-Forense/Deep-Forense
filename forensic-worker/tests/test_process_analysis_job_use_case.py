"""Tests de T2.M8 — ProcessAnalysisJobUseCase.

Aceptación del backlog: un artifact que lanza excepción se marca FAILED sin
detener a los demás; el job pasa a FAILED solo si TODOS fallan. Todos los
puertos son fakes en memoria (sin Mongo/MinIO/APIs reales).
"""
from typing import Optional

from app.application.use_cases.process_analysis_job_use_case import ProcessAnalysisJobUseCase
from app.domain.entities.artifact import Artifact
from app.domain.entities.artifact_analysis import ArtifactAnalysis
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort
from app.domain.ports.benford_analyzer_port import BenfordAnalyzerPort
from app.domain.ports.dct_analyzer_port import DctAnalyzerPort
from app.domain.ports.ela_analyzer_port import ElaAnalyzerPort, ElaResult
from app.domain.ports.exif_analyzer_port import ExifAnalyzerPort
from app.domain.ports.image_cognitive_analyzer_port import ImageCognitiveAnalyzerPort
from app.domain.ports.ocr_port import EmbeddedImage, OcrExtraction, OcrPort
from app.domain.ports.storage_port import StoragePort
from app.domain.ports.text_cognitive_analyzer_port import (
    TextCognitiveAnalyzerPort,
    TextCognitiveResult,
)
from app.domain.services.benford_applicability_service import BenfordApplicabilityService
from app.domain.services.consolidation_service import ConsolidationService
from app.domain.services.fraud_scoring_service import FraudScoringService
from app.domain.services.image_classification_service import ImageClassificationService

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


class FakeRepository(AnalysisJobRepositoryPort):
    def __init__(self, artifacts: list, status: str = "PENDING") -> None:
        self._artifacts = artifacts
        self.status = status
        self.saved_results: dict = {}
        self.final: Optional[tuple] = None

    async def get_job_status(self, job_id: str) -> Optional[str]:
        return self.status

    async def get_artifacts(self, job_id: str) -> list:
        return self._artifacts

    async def mark_processing(self, job_id: str) -> None:
        self.status = "PROCESSING"

    async def save_artifact_result(self, job_id, artifact, analysis) -> None:
        self.saved_results[artifact.artifact_id] = (artifact.status, analysis)

    async def complete_job(self, job_id, status, consolidated) -> None:
        self.final = (status, consolidated)


class FakeStorage(StoragePort):
    def __init__(self, blobs: dict) -> None:
        self._blobs = blobs
        self.saved: dict = {}

    async def get(self, storage_ref: str) -> bytes:
        return self._blobs[storage_ref]

    async def save(self, path: str, content: bytes) -> str:
        self.saved[path] = content
        return f"bucket/{path}"


class FakeExif(ExifAnalyzerPort):
    async def analyze(self, image_bytes: bytes) -> float:
        return 0.2


class FakeEla(ElaAnalyzerPort):
    async def analyze(self, image_bytes: bytes) -> ElaResult:
        return ElaResult(score=0.4, heatmap_png=b"\x89PNGfake")


class BrokenEla(ElaAnalyzerPort):
    async def analyze(self, image_bytes: bytes) -> ElaResult:
        raise RuntimeError("ELA explotó")


class FakeDct(DctAnalyzerPort):
    async def extract_coefficients(self, image_bytes: bytes):
        return [1.0, 2.0, 3.0]


class FakeBenford(BenfordAnalyzerPort):
    async def score(self, values) -> float:
        return 0.1


class FakeOcr(OcrPort):
    async def extract_text(self, content: bytes) -> str:
        return "FACTURA total 100"


class FakeOcrWithImage(FakeOcr):
    async def extract_with_metadata(self, content: bytes) -> OcrExtraction:
        return OcrExtraction(
            text="FACTURA total 100",
            page_count=1,
            analyzed_pages=1,
            embedded_images=1,
            visual_images=(EmbeddedImage(JPEG, 1, 800, 600),),
        )


class FakeTextAnalyzer(TextCognitiveAnalyzerPort):
    def __init__(self, document_type="invoice", amounts=None) -> None:
        self._document_type = document_type
        self._amounts = amounts if amounts is not None else [10 ** (i / 10) for i in range(31)]

    async def analyze(self, text: str) -> TextCognitiveResult:
        return TextCognitiveResult(
            document_type=self._document_type, financial_amounts=self._amounts, ai_flags=["f1"]
        )


class FakeImageAnalyzer(ImageCognitiveAnalyzerPort):
    async def analyze(self, image_bytes: bytes) -> list:
        return ["cloned_region"]


class BrokenImageAnalyzer(ImageCognitiveAnalyzerPort):
    async def analyze(self, image_bytes: bytes) -> list:
        raise RuntimeError("cuota agotada")


def _use_case(repository, storage, ela=None, text_analyzer=None, ocr=None,
              image_analyzer=None) -> ProcessAnalysisJobUseCase:
    return ProcessAnalysisJobUseCase(
        repository=repository,
        storage=storage,
        exif_analyzer=FakeExif(),
        ela_analyzer=ela or FakeEla(),
        dct_analyzer=FakeDct(),
        benford_analyzer=FakeBenford(),
        ocr=ocr or FakeOcr(),
        text_analyzer=text_analyzer or FakeTextAnalyzer(),
        image_analyzer=image_analyzer or FakeImageAnalyzer(),
        benford_applicability=BenfordApplicabilityService(min_amount_count=15),
        fraud_scoring=FraudScoringService(),
        consolidation=ConsolidationService(),  # worst_case_dominates default
        image_classification=ImageClassificationService(),
    )


async def test_failing_artifact_does_not_stop_the_others():
    artifacts = [
        Artifact("a-img", "IMAGE", "bucket/img.jpg"),
        Artifact("a-txt", "TEXT", "bucket/doc.pdf"),
    ]
    repository = FakeRepository(artifacts)
    storage = FakeStorage({"bucket/img.jpg": JPEG, "bucket/doc.pdf": b"texto plano utf8"})
    use_case = _use_case(repository, storage, ela=BrokenEla())  # la imagen fallará

    result = await use_case.execute("job-1")

    assert repository.saved_results["a-img"][0] == "FAILED"
    assert repository.saved_results["a-img"][1] is None
    assert repository.saved_results["a-txt"][0] == "COMPLETED"
    assert result["status"] == "COMPLETED"  # al menos 1 completó
    assert repository.final[0] == "COMPLETED"
    # Sprint 3: la consolidación real solo considera los artifacts completados.
    consolidated = repository.final[1]
    assert consolidated["policy_applied"] == "worst_case_dominates"
    assert consolidated["dominant_artifact"] == "a-txt"


async def test_job_fails_only_if_all_artifacts_fail():
    artifacts = [Artifact("a1", "IMAGE", "bucket/1.jpg"), Artifact("a2", "IMAGE", "bucket/2.jpg")]
    repository = FakeRepository(artifacts)
    storage = FakeStorage({"bucket/1.jpg": JPEG, "bucket/2.jpg": JPEG})
    use_case = _use_case(repository, storage, ela=BrokenEla())

    result = await use_case.execute("job-2")

    assert result["status"] == "FAILED"
    assert repository.final == ("FAILED", None)
    assert all(status == "FAILED" for status, _ in repository.saved_results.values())


async def test_image_artifact_gets_full_analysis_and_heatmap_saved():
    artifacts = [Artifact("a-img", "IMAGE", "bucket/img.jpg")]
    repository = FakeRepository(artifacts)
    storage = FakeStorage({"bucket/img.jpg": JPEG})

    await _use_case(repository, storage).execute("job-3")

    status, analysis = repository.saved_results["a-img"]
    assert status == "COMPLETED"
    assert analysis.exif_score == 0.2
    assert analysis.ela_score == 0.4
    assert analysis.benford_applicable is True  # es JPEG
    assert analysis.dct_benford_score == 0.1
    assert analysis.gemini_flags == ["cloned_region"]
    assert analysis.ai_flags == ["cloned_region"]
    assert "jobs/job-3/artifacts/a-img/ela_heatmap.png" in storage.saved
    assert analysis.ela_heatmap_ref == "bucket/jobs/job-3/artifacts/a-img/ela_heatmap.png"


async def test_non_jpeg_image_skips_dct_without_penalty():
    artifacts = [Artifact("a-png", "IMAGE", "bucket/img.png")]
    repository = FakeRepository(artifacts)
    storage = FakeStorage({"bucket/img.png": PNG})

    await _use_case(repository, storage).execute("job-4")

    _, analysis = repository.saved_results["a-png"]
    assert analysis.benford_applicable is False
    assert analysis.dct_benford_score is None
    assert analysis.ela_score is not None  # las demás señales sí corren


async def test_non_financial_text_never_gets_benford_score():
    artifacts = [Artifact("a-txt", "TEXT", "bucket/carta.pdf")]
    repository = FakeRepository(artifacts)
    storage = FakeStorage({"bucket/carta.pdf": b"querida abuela"})
    many_amounts = [float(i) for i in range(1, 40)]
    use_case = _use_case(
        repository, storage, text_analyzer=FakeTextAnalyzer("letter", many_amounts)
    )

    await use_case.execute("job-5")

    _, analysis = repository.saved_results["a-txt"]
    assert analysis.benford_applicable is False
    assert analysis.benford_score is None
    assert analysis.document_type == "letter"


async def test_financial_text_with_enough_amounts_gets_benford_score():
    artifacts = [Artifact("a-txt", "TEXT", "bucket/factura.pdf")]
    repository = FakeRepository(artifacts)
    storage = FakeStorage({"bucket/factura.pdf": b"factura"})

    await _use_case(repository, storage).execute("job-6")

    _, analysis = repository.saved_results["a-txt"]
    assert analysis.benford_applicable is True
    assert analysis.benford_score == 0.1


async def test_pdf_embedded_image_keeps_technical_evidence_if_ai_fails():
    artifacts = [Artifact("a-txt", "TEXT", "bucket/factura.pdf")]
    repository = FakeRepository(artifacts)
    storage = FakeStorage({"bucket/factura.pdf": b"%PDF fake"})
    use_case = _use_case(
        repository, storage, ocr=FakeOcrWithImage(), image_analyzer=BrokenImageAnalyzer()
    )

    result = await use_case.execute("job-visual")

    assert result["status"] == "COMPLETED"
    _, analysis = repository.saved_results["a-txt"]
    assert analysis.document_visual_score == 0.2333
    assert analysis.document_visual_evidence[0]["cognitive_available"] is False
    assert analysis.document_visual_evidence[0]["ela_score"] == 0.4
    assert analysis.document_visual_heatmap_ref.endswith("document_image_1_ela.png")


async def test_direct_image_keeps_technical_evidence_if_ai_fails():
    artifacts = [Artifact("a-img", "IMAGE", "bucket/img.jpg")]
    repository = FakeRepository(artifacts)
    storage = FakeStorage({"bucket/img.jpg": JPEG})

    result = await _use_case(
        repository, storage, image_analyzer=BrokenImageAnalyzer()
    ).execute("job-image-partial")

    assert result["status"] == "COMPLETED"
    _, analysis = repository.saved_results["a-img"]
    assert analysis.exif_score == 0.2
    assert analysis.ela_score == 0.4
    assert analysis.cognitive_available is False
    assert analysis.image_classification == "INCONCLUSIVE"
    assert result["consolidated"]["verdict"] == "INCONCLUSIVE"
    assert result["consolidated"]["authenticity_percentage"] is None


async def test_already_completed_job_is_idempotent():
    repository = FakeRepository([], status="COMPLETED")
    storage = FakeStorage({})

    result = await _use_case(repository, storage).execute("job-7")

    assert result == {"job_id": "job-7", "status": "COMPLETED"}
    assert repository.final is None  # no se reescribió nada
