"""Pruebas del análisis de una URL directa de imagen."""
import pytest

from app.application.dto.submit_url_analysis_command import SubmitUrlAnalysisCommand
from app.application.use_cases.submit_url_analysis_use_case import SubmitUrlAnalysisUseCase
from app.domain.exceptions import UnsupportedUrlContentError, UrlDownloadError
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort
from app.domain.ports.image_inspector_port import ImageInspectorPort, ImageProbe
from app.domain.ports.storage_port import StoragePort
from app.domain.ports.task_queue_port import TaskQueuePort
from app.domain.ports.url_downloader_port import UrlDownloaderPort
from app.domain.value_objects.downloaded_resource import DownloadedResource

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
WEBP = b"RIFF\x10\x00\x00\x00WEBP" + b"\x00" * 16


class FakeDownloader(UrlDownloaderPort):
    def __init__(self, resource=None, error=None):
        self.resource = resource
        self.error = error

    async def download(self, url: str) -> DownloadedResource:
        if self.error:
            raise self.error
        return self.resource


class FakeInspector(ImageInspectorPort):
    def __init__(self, error=None):
        self.error = error

    async def inspect(self, content: bytes) -> ImageProbe:
        if self.error:
            raise self.error
        return ImageProbe(width=800, height=600, perceptual_hash=123)


class FakeStorage(StoragePort):
    def __init__(self):
        self.saved = {}

    async def save(self, path: str, content: bytes) -> str:
        self.saved[path] = content
        return f"bucket/{path}"

    async def get(self, storage_ref: str) -> bytes:
        raise NotImplementedError


class FakeRepository(AnalysisJobRepositoryPort):
    def __init__(self):
        self.saved_job = None

    async def save(self, job) -> None:
        self.saved_job = job

    async def find_by_id(self, job_id: str):
        return None

    async def find_by_user(self, user_id, page, page_size, verdict=None):
        return [], 0


class FakeQueue(TaskQueuePort):
    def __init__(self):
        self.enqueued = []

    def enqueue_analysis(self, job_id: str) -> None:
        self.enqueued.append(job_id)


def _use_case(resource, inspector_error=None, download_error=None):
    repository, storage, queue = FakeRepository(), FakeStorage(), FakeQueue()
    use_case = SubmitUrlAnalysisUseCase(
        repository=repository,
        storage=storage,
        task_queue=queue,
        downloader=FakeDownloader(resource, download_error),
        image_inspector=FakeInspector(inspector_error),
    )
    return use_case, repository, storage, queue


@pytest.mark.parametrize(
    ("content", "content_type", "file_name"),
    [(JPEG, "image/jpeg", "foto.jpg"), (PNG, "image/png", "foto.png"), (WEBP, "image/webp", "foto.webp")],
)
async def test_direct_image_enters_the_image_pipeline(content, content_type, file_name):
    resource = DownloadedResource(content=content, content_type=content_type, file_name=file_name)
    use_case, repository, storage, queue = _use_case(resource)

    job = await use_case.execute(SubmitUrlAnalysisCommand(user_id="u1", url="https://cdn.example/foto"))

    artifact = job.artifacts[0]
    assert repository.saved_job is job
    assert len(job.artifacts) == 1
    assert str(artifact.type) == "IMAGE"
    assert artifact.origin == "DIRECT_URL"
    assert list(storage.saved.values()) == [content]
    assert next(iter(storage.saved)).endswith(f"-{file_name}")
    assert queue.enqueued == [job.job_id]


@pytest.mark.parametrize(
    "resource",
    [
        DownloadedResource("<html>página</html>".encode(), "text/html", "pagina"),
        DownloadedResource(b"%PDF-1.7", "application/pdf", "archivo.pdf"),
        DownloadedResource(b"no es imagen", "image/jpeg", "imagen.jpg"),
    ],
)
async def test_page_pdf_and_false_content_type_are_rejected(resource):
    use_case, repository, storage, queue = _use_case(resource)

    with pytest.raises(UnsupportedUrlContentError, match="imagen directa"):
        await use_case.execute(SubmitUrlAnalysisCommand(user_id=None, url="https://example.com/recurso"))

    assert repository.saved_job is None
    assert storage.saved == {}
    assert queue.enqueued == []


async def test_corrupt_image_is_rejected_before_creating_job():
    resource = DownloadedResource(JPEG, "image/jpeg", "rota.jpg")
    use_case, repository, _, queue = _use_case(resource, inspector_error=ValueError("invalid"))

    with pytest.raises(UnsupportedUrlContentError, match="dañada"):
        await use_case.execute(SubmitUrlAnalysisCommand(user_id=None, url="https://example.com/rota.jpg"))

    assert repository.saved_job is None
    assert queue.enqueued == []


async def test_download_error_is_propagated_without_creating_job():
    use_case, repository, _, queue = _use_case(None, download_error=UrlDownloadError("no encontrada"))

    with pytest.raises(UrlDownloadError, match="no encontrada"):
        await use_case.execute(SubmitUrlAnalysisCommand(user_id=None, url="https://example.com/no.jpg"))

    assert repository.saved_job is None
    assert queue.enqueued == []
