"""Caso de uso: analizar exclusivamente una URL directa de imagen."""
from uuid import uuid4

from app.application.dto.submit_url_analysis_command import SubmitUrlAnalysisCommand
from app.application.ports.submit_url_analysis_input_port import SubmitUrlAnalysisInputPort
from app.domain.aggregates.analysis_job import AnalysisJob
from app.domain.entities.artifact import Artifact
from app.domain.exceptions import UnsupportedUrlContentError
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort
from app.domain.ports.image_inspector_port import ImageInspectorPort
from app.domain.ports.storage_port import StoragePort
from app.domain.ports.task_queue_port import TaskQueuePort
from app.domain.ports.url_downloader_port import UrlDownloaderPort
from app.domain.value_objects.artifact_type import ArtifactType


def _image_format(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "webp"
    return None


class SubmitUrlAnalysisUseCase(SubmitUrlAnalysisInputPort):
    def __init__(self, repository: AnalysisJobRepositoryPort, storage: StoragePort,
                 task_queue: TaskQueuePort, downloader: UrlDownloaderPort,
                 image_inspector: ImageInspectorPort) -> None:
        self._repository = repository
        self._storage = storage
        self._task_queue = task_queue
        self._downloader = downloader
        self._image_inspector = image_inspector

    async def execute(self, command: SubmitUrlAnalysisCommand) -> AnalysisJob:
        resource = await self._downloader.download(command.url)
        detected_format = _image_format(resource.content)
        if detected_format is None:
            raise UnsupportedUrlContentError(
                "El enlace no contiene una imagen directa JPEG, PNG o WEBP. "
                "Corrige el enlace y vuelve a intentarlo."
            )
        try:
            await self._image_inspector.inspect(resource.content)
        except ValueError as exc:
            raise UnsupportedUrlContentError(
                "La imagen del enlace está dañada o no puede leerse. "
                "Comprueba el enlace y vuelve a intentarlo."
            ) from exc

        original_name = resource.file_name or f"imagen.{detected_format}"
        storage_ref = await self._storage.save(
            path=f"uploads/{uuid4().hex}-{original_name}", content=resource.content
        )
        artifact = Artifact.create(ArtifactType("IMAGE"), storage_ref, origin="DIRECT_URL")
        job = AnalysisJob.create(user_id=command.user_id, artifacts=[artifact])
        await self._repository.save(job)
        self._task_queue.enqueue_analysis(job.job_id)
        return job
