"""Tests de FOR-97 (URL directa) y FOR-98/FOR-134 (scraping DOM).

Puertos falsos en memoria: sin red, sin MinIO, sin Mongo, sin Redis, sin
Scrapfly real. Criterio de aceptación FOR-98: una URL con texto e imágenes
genera un job con más de un artifact.
"""
import pytest

from app.application.dto.submit_url_analysis_command import SubmitUrlAnalysisCommand
from app.application.use_cases.submit_url_analysis_use_case import SubmitUrlAnalysisUseCase
from app.domain.exceptions import UnsupportedUrlContentError, UrlDownloadError
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort
from app.domain.ports.image_inspector_port import ImageInspectorPort, ImageProbe
from app.domain.ports.storage_port import StoragePort
from app.domain.ports.task_queue_port import TaskQueuePort
from app.domain.ports.url_downloader_port import UrlDownloaderPort
from app.domain.ports.web_scraper_port import ScrapedImage, ScrapedPage, WebScraperPort
from app.domain.services.artifact_selection_service import ArtifactSelectionService
from app.domain.value_objects.downloaded_resource import DownloadedResource

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
PDF = b"%PDF-1.7 fake"


class FakeDownloader(UrlDownloaderPort):
    """Devuelve un recurso distinto por URL (para el flujo de scraping)."""

    def __init__(self, resources: dict) -> None:
        self._resources = resources

    async def download(self, url: str) -> DownloadedResource:
        resource = self._resources.get(url)
        if resource is None:
            raise UrlDownloadError(f"sin respuesta para {url}")
        return resource


class FakeScraper(WebScraperPort):
    def __init__(self, page: ScrapedPage) -> None:
        self._page = page

    async def scrape(self, url: str) -> ScrapedPage:
        return self._page


class FakeInspector(ImageInspectorPort):
    """Dimensiones y hash fijados por URL mediante un dict {content: probe}."""

    def __init__(self, probes: dict) -> None:
        self._probes = probes

    async def inspect(self, content: bytes) -> ImageProbe:
        return self._probes[content]


class FakeStorage(StoragePort):
    def __init__(self) -> None:
        self.saved: dict = {}

    async def save(self, path: str, content: bytes) -> str:
        self.saved[path] = content
        return f"bucket/{path}"

    async def get(self, storage_ref: str) -> bytes:
        raise NotImplementedError


class FakeRepository(AnalysisJobRepositoryPort):
    def __init__(self) -> None:
        self.saved_job = None

    async def save(self, job) -> None:
        self.saved_job = job

    async def find_by_id(self, job_id: str):
        return None

    async def find_by_user(self, user_id, page, page_size, verdict=None):
        return [], 0


class FakeQueue(TaskQueuePort):
    def __init__(self) -> None:
        self.enqueued: list = []

    def enqueue_analysis(self, job_id: str) -> None:
        self.enqueued.append(job_id)


def _use_case(resources, page=None, probes=None, max_images=5):
    repository, storage, queue = FakeRepository(), FakeStorage(), FakeQueue()
    use_case = SubmitUrlAnalysisUseCase(
        repository=repository,
        storage=storage,
        task_queue=queue,
        downloader=FakeDownloader(resources),
        scraper=FakeScraper(page or ScrapedPage(text="", images=[])),
        image_inspector=FakeInspector(probes or {}),
        artifact_selection=ArtifactSelectionService(max_candidates=max_images),
    )
    return use_case, repository, storage, queue


# --- FOR-97: URL directa -----------------------------------------------------

async def test_direct_image_url_creates_image_artifact():
    url = "http://x.com/foto.jpg"
    resource = DownloadedResource(content=JPEG, content_type="image/jpeg", file_name="foto.jpg")
    use_case, repository, storage, queue = _use_case({url: resource})

    job = await use_case.execute(SubmitUrlAnalysisCommand(user_id=None, url=url))

    assert repository.saved_job is job
    assert len(job.artifacts) == 1
    assert str(job.artifacts[0].type) == "IMAGE"
    assert job.artifacts[0].origin == "UPLOAD"
    assert storage.saved["uploads/foto.jpg"] == JPEG
    assert queue.enqueued == [job.job_id]


async def test_direct_pdf_url_creates_text_artifact():
    url = "http://x.com/doc.pdf"
    resource = DownloadedResource(content=PDF, content_type="application/pdf", file_name="doc.pdf")
    use_case, repository, _, _ = _use_case({url: resource})

    job = await use_case.execute(SubmitUrlAnalysisCommand(user_id=None, url=url))

    assert str(job.artifacts[0].type) == "TEXT"


async def test_generic_content_type_falls_back_to_url_extension():
    url = "http://cdn.x.com/media/foto.jpg?v=2"
    resource = DownloadedResource(
        content=JPEG, content_type="application/octet-stream", file_name="foto.jpg"
    )
    use_case, repository, _, _ = _use_case({url: resource})

    job = await use_case.execute(SubmitUrlAnalysisCommand(user_id=None, url=url))

    assert str(job.artifacts[0].type) == "IMAGE"


async def test_unknown_content_type_is_rejected():
    url = "http://x.com/blob"
    resource = DownloadedResource(
        content=b"????", content_type="application/octet-stream", file_name="blob"
    )
    use_case, repository, _, queue = _use_case({url: resource})

    with pytest.raises(UnsupportedUrlContentError):
        await use_case.execute(SubmitUrlAnalysisCommand(user_id=None, url=url))

    assert repository.saved_job is None
    assert queue.enqueued == []


# --- FOR-98: scraping de página HTML ----------------------------------------

HTML_URL = "https://noticia.example.com/articulo"
HTML_RESOURCE = DownloadedResource(
    content=b"<html>...</html>", content_type="text/html", file_name="articulo"
)
IMG_A = b"IMG-A" + b"\x00" * 10
IMG_B = b"IMG-B" + b"\x00" * 10


def _scraping_setup(max_images=5):
    page = ScrapedPage(
        text="Titular del articulo\nParrafo principal con contenido.",
        images=[
            ScrapedImage(url="https://cdn.example.com/grande.jpg", section="main"),
            ScrapedImage(url="https://cdn.example.com/icono.png", section="header"),
        ],
    )
    resources = {
        HTML_URL: HTML_RESOURCE,
        "https://cdn.example.com/grande.jpg": DownloadedResource(
            content=IMG_A, content_type="image/jpeg", file_name="grande.jpg"
        ),
        "https://cdn.example.com/icono.png": DownloadedResource(
            content=IMG_B, content_type="image/png", file_name="icono.png"
        ),
    }
    probes = {
        IMG_A: ImageProbe(width=800, height=600, perceptual_hash=0b1010),
        IMG_B: ImageProbe(width=32, height=32, perceptual_hash=0b0101),  # icono: se descarta
    }
    return _use_case(resources, page=page, probes=probes, max_images=max_images)


async def test_html_url_creates_text_plus_image_artifacts():
    use_case, repository, storage, queue = _scraping_setup()

    job = await use_case.execute(SubmitUrlAnalysisCommand(user_id="u1", url=HTML_URL))

    # Aceptación FOR-98: más de un artifact (1 TEXT + imágenes relevantes).
    assert len(job.artifacts) == 2
    text_artifact, image_artifact = job.artifacts
    assert str(text_artifact.type) == "TEXT"
    assert text_artifact.origin == "SCRAPED_DOM"
    assert str(image_artifact.type) == "IMAGE"
    assert image_artifact.origin == "SCRAPED_DOM_IMAGE"
    # El texto scrapeado quedó en storage:
    text_blobs = [c for p, c in storage.saved.items() if p.startswith("scraped/") and p.endswith(".txt")]
    assert text_blobs == ["Titular del articulo\nParrafo principal con contenido.".encode("utf-8")]
    assert queue.enqueued == [job.job_id]


async def test_small_images_are_filtered_out_by_selection():
    use_case, repository, storage, _ = _scraping_setup()

    job = await use_case.execute(SubmitUrlAnalysisCommand(user_id=None, url=HTML_URL))

    image_artifacts = [a for a in job.artifacts if str(a.type) == "IMAGE"]
    assert len(image_artifacts) == 1  # el icono 32x32 quedó fuera (FOR-99)
    saved_images = [c for p, c in storage.saved.items() if not p.endswith(".txt")]
    assert saved_images == [IMG_A]


async def test_broken_candidate_image_does_not_abort_scraping():
    use_case, repository, storage, _ = _scraping_setup()
    # grande.jpg no responde: solo queda el texto (icono se filtra por tamaño).
    del use_case._downloader._resources["https://cdn.example.com/grande.jpg"]

    job = await use_case.execute(SubmitUrlAnalysisCommand(user_id=None, url=HTML_URL))

    assert [str(a.type) for a in job.artifacts] == ["TEXT"]


async def test_empty_page_is_rejected():
    use_case, _, _, _ = _use_case({HTML_URL: HTML_RESOURCE}, page=ScrapedPage(text="  ", images=[]))

    with pytest.raises(UnsupportedUrlContentError, match="no contiene"):
        await use_case.execute(SubmitUrlAnalysisCommand(user_id=None, url=HTML_URL))
