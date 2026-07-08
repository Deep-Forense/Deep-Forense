"""Tests de Tarea A (FOR-97/HU3.2) — SubmitUrlAnalysisUseCase.

Puertos falsos en memoria: sin red, sin MinIO, sin Mongo, sin Redis.
"""
import pytest

from app.application.dto.submit_url_analysis_command import SubmitUrlAnalysisCommand
from app.application.use_cases.submit_url_analysis_use_case import SubmitUrlAnalysisUseCase
from app.domain.exceptions import UnsupportedUrlContentError
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort
from app.domain.ports.storage_port import StoragePort
from app.domain.ports.task_queue_port import TaskQueuePort
from app.domain.ports.url_downloader_port import UrlDownloaderPort
from app.domain.value_objects.downloaded_resource import DownloadedResource

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
PDF = b"%PDF-1.7 fake"
HTML = b"<html><body>una pagina</body></html>"


class FakeDownloader(UrlDownloaderPort):
    def __init__(self, resource: DownloadedResource) -> None:
        self._resource = resource

    async def download(self, url: str) -> DownloadedResource:
        return self._resource


class FakeStorage(StoragePort):
    def __init__(self) -> None:
        self.saved: dict = {}

    async def save(self, path: str, content: bytes) -> str:
        self.saved[path] = content
        return f"bucket/{path}"


class FakeRepository(AnalysisJobRepositoryPort):
    def __init__(self) -> None:
        self.saved_job = None

    async def save(self, job) -> None:
        self.saved_job = job

    async def find_by_id(self, job_id: str):
        return None


class FakeQueue(TaskQueuePort):
    def __init__(self) -> None:
        self.enqueued: list = []

    def enqueue_analysis(self, job_id: str) -> None:
        self.enqueued.append(job_id)


def _use_case(resource: DownloadedResource):
    repository, storage, queue = FakeRepository(), FakeStorage(), FakeQueue()
    use_case = SubmitUrlAnalysisUseCase(
        repository=repository,
        storage=storage,
        task_queue=queue,
        downloader=FakeDownloader(resource),
    )
    return use_case, repository, storage, queue


async def test_direct_image_url_creates_image_artifact():
    resource = DownloadedResource(content=JPEG, content_type="image/jpeg", file_name="foto.jpg")
    use_case, repository, storage, queue = _use_case(resource)

    job_id = await use_case.execute(SubmitUrlAnalysisCommand(user_id=None, url="http://x.com/foto.jpg"))

    job = repository.saved_job
    assert job is not None and job.job_id == job_id
    assert len(job.artifacts) == 1
    assert str(job.artifacts[0].type) == "IMAGE"
    assert storage.saved["uploads/foto.jpg"] == JPEG  # mismo flujo que un upload
    assert queue.enqueued == [job_id]


async def test_direct_pdf_url_creates_text_artifact():
    resource = DownloadedResource(content=PDF, content_type="application/pdf", file_name="doc.pdf")
    use_case, repository, _, _ = _use_case(resource)

    await use_case.execute(SubmitUrlAnalysisCommand(user_id=None, url="http://x.com/doc.pdf"))

    assert str(repository.saved_job.artifacts[0].type) == "TEXT"


async def test_html_url_is_rejected_as_sprint_3():
    resource = DownloadedResource(content=HTML, content_type="text/html", file_name="index.html")
    use_case, repository, _, queue = _use_case(resource)

    with pytest.raises(UnsupportedUrlContentError, match="Sprint 3"):
        await use_case.execute(SubmitUrlAnalysisCommand(user_id=None, url="http://x.com/pagina"))

    assert repository.saved_job is None  # no se creó nada
    assert queue.enqueued == []


async def test_generic_content_type_falls_back_to_url_extension():
    resource = DownloadedResource(
        content=JPEG, content_type="application/octet-stream", file_name="foto.jpg"
    )
    use_case, repository, _, _ = _use_case(resource)

    await use_case.execute(
        SubmitUrlAnalysisCommand(user_id=None, url="http://cdn.x.com/media/foto.jpg?v=2")
    )

    assert str(repository.saved_job.artifacts[0].type) == "IMAGE"


async def test_generic_content_type_without_known_extension_is_rejected():
    resource = DownloadedResource(
        content=b"????", content_type="application/octet-stream", file_name="blob"
    )
    use_case, _, _, _ = _use_case(resource)

    with pytest.raises(UnsupportedUrlContentError):
        await use_case.execute(SubmitUrlAnalysisCommand(user_id=None, url="http://x.com/blob"))
