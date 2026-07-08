"""Caso de uso: SubmitUrlAnalysisUseCase (FOR-97 / HU3.2).

Soporta el caso simple de Sprint 1/2: la URL apunta DIRECTO a una imagen o
PDF. Descarga el contenido, crea 1 artifact (IMAGE o TEXT) y sigue el mismo
flujo que un upload de archivo (MinIO -> Mongo -> Redis).

El caso de página HTML con scraping (Scrapfly + ArtifactSelectionService)
es Sprint 3 (FOR-98/T3.M1): aquí se rechaza con UnsupportedUrlContentError.
"""
from urllib.parse import urlparse

from app.application.dto.submit_url_analysis_command import SubmitUrlAnalysisCommand
from app.application.ports.submit_url_analysis_input_port import SubmitUrlAnalysisInputPort
from app.domain.aggregates.analysis_job import AnalysisJob
from app.domain.entities.artifact import Artifact
from app.domain.exceptions import UnsupportedUrlContentError
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort
from app.domain.ports.storage_port import StoragePort
from app.domain.ports.task_queue_port import TaskQueuePort
from app.domain.ports.url_downloader_port import UrlDownloaderPort
from app.domain.value_objects.artifact_type import ArtifactType
from app.domain.value_objects.downloaded_resource import DownloadedResource

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
_PDF_EXTENSIONS = {".pdf"}
# Content-types que no aportan información (el servidor no supo decir qué es):
# en esos casos se decide por la extensión de la URL.
_GENERIC_CONTENT_TYPES = {"", "application/octet-stream", "binary/octet-stream"}


def _url_extension(url: str) -> str:
    path = urlparse(url).path
    dot = path.rfind(".")
    return path[dot:].lower() if dot != -1 else ""


def _resolve_artifact_type(url: str, resource: DownloadedResource) -> str:
    """IMAGE | TEXT según content-type (prioridad) o extensión de la URL.

    Lanza UnsupportedUrlContentError si el contenido es HTML u otro tipo no
    soportado (eso es scraping, Sprint 3).
    """
    content_type = resource.content_type.lower()

    if content_type.startswith("image/"):
        return "IMAGE"
    if content_type == "application/pdf":
        return "TEXT"

    if content_type in _GENERIC_CONTENT_TYPES:
        extension = _url_extension(url)
        if extension in _IMAGE_EXTENSIONS:
            return "IMAGE"
        if extension in _PDF_EXTENSIONS:
            return "TEXT"

    raise UnsupportedUrlContentError(
        "La URL no apunta directo a una imagen o PDF. "
        "El análisis de páginas HTML (scraping) está disponible a partir de Sprint 3."
    )


class SubmitUrlAnalysisUseCase(SubmitUrlAnalysisInputPort):
    def __init__(
        self,
        repository: AnalysisJobRepositoryPort,
        storage: StoragePort,
        task_queue: TaskQueuePort,
        downloader: UrlDownloaderPort,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._task_queue = task_queue
        self._downloader = downloader

    async def execute(self, command: SubmitUrlAnalysisCommand) -> str:
        resource = await self._downloader.download(command.url)
        artifact_type = ArtifactType(_resolve_artifact_type(command.url, resource))

        # Mismo flujo que un upload (T1.M1/M2/M3): MinIO antes de encolar.
        storage_ref = await self._storage.save(
            path=f"uploads/{resource.file_name}",
            content=resource.content,
        )
        artifact = Artifact.create(artifact_type=artifact_type, storage_ref=storage_ref)
        job = AnalysisJob.create(user_id=command.user_id, artifacts=[artifact])

        await self._repository.save(job)
        self._task_queue.enqueue_analysis(job.job_id)

        return job.job_id
