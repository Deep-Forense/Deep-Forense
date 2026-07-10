"""Caso de uso: SubmitUrlAnalysisUseCase (FOR-97 + FOR-98/FOR-134).

Tres caminos según el contenido de la URL:

  1. Imagen o PDF directo (FOR-97/HU3.2): descarga y crea 1 artifact
     (IMAGE o TEXT, origin=UPLOAD), mismo flujo que un upload.
  2. Página HTML (FOR-98/HU3.3, Sprint 3): scrapea vía WebScraperPort
     (Scrapfly) y crea 1 artifact TEXT (origin=SCRAPED_DOM) con el texto
     principal + hasta N artifacts IMAGE (origin=SCRAPED_DOM_IMAGE) con las
     imágenes candidatas relevantes, filtradas por ArtifactSelectionService
     (FOR-99): tamaño mínimo, dedupe perceptual, prioridad de contenido
     principal, tope MAX_IMAGES_PER_JOB.
  3. Cualquier otro tipo: UnsupportedUrlContentError -> HTTP 400.
"""
import logging
from urllib.parse import urlparse
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
from app.domain.ports.web_scraper_port import WebScraperPort
from app.domain.services.artifact_selection_service import ArtifactSelectionService
from app.domain.value_objects.artifact_type import ArtifactType
from app.domain.value_objects.downloaded_resource import DownloadedResource
from app.domain.value_objects.image_candidate import ImageCandidate

logger = logging.getLogger(__name__)

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
_PDF_EXTENSIONS = {".pdf"}
_HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}
# Content-types que no aportan información (el servidor no supo decir qué es):
# en esos casos se decide por la extensión de la URL.
_GENERIC_CONTENT_TYPES = {"", "application/octet-stream", "binary/octet-stream"}


def _url_extension(url: str) -> str:
    path = urlparse(url).path
    dot = path.rfind(".")
    return path[dot:].lower() if dot != -1 else ""


def _resolve_direct_artifact_type(url: str, resource: DownloadedResource) -> str:
    """IMAGE | TEXT para URLs directas, según content-type (prioridad) o
    extensión. Lanza UnsupportedUrlContentError para tipos no soportados."""
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
        "La URL no apunta a una imagen, PDF o página HTML soportada."
    )


class SubmitUrlAnalysisUseCase(SubmitUrlAnalysisInputPort):
    def __init__(
        self,
        repository: AnalysisJobRepositoryPort,
        storage: StoragePort,
        task_queue: TaskQueuePort,
        downloader: UrlDownloaderPort,
        scraper: WebScraperPort,
        image_inspector: ImageInspectorPort,
        artifact_selection: ArtifactSelectionService,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._task_queue = task_queue
        self._downloader = downloader
        self._scraper = scraper
        self._image_inspector = image_inspector
        self._artifact_selection = artifact_selection

    async def execute(self, command: SubmitUrlAnalysisCommand) -> AnalysisJob:
        resource = await self._downloader.download(command.url)

        if resource.content_type.lower() in _HTML_CONTENT_TYPES:
            artifacts = await self._scrape_artifacts(command.url)  # FOR-98
        else:
            artifacts = [await self._direct_artifact(command.url, resource)]  # FOR-97

        job = AnalysisJob.create(user_id=command.user_id, artifacts=artifacts)
        await self._repository.save(job)
        self._task_queue.enqueue_analysis(job.job_id)
        return job

    async def _direct_artifact(self, url: str, resource: DownloadedResource) -> Artifact:
        artifact_type = ArtifactType(_resolve_direct_artifact_type(url, resource))
        storage_ref = await self._storage.save(
            path=f"uploads/{resource.file_name}", content=resource.content
        )
        return Artifact.create(artifact_type=artifact_type, storage_ref=storage_ref)

    async def _scrape_artifacts(self, url: str) -> list:
        page = await self._scraper.scrape(url)
        artifacts = []

        text = page.text.strip()
        if text:
            storage_ref = await self._storage.save(
                path=f"scraped/{uuid4().hex}.txt", content=text.encode("utf-8")
            )
            artifacts.append(
                Artifact.create(
                    artifact_type=ArtifactType("TEXT"),
                    storage_ref=storage_ref,
                    origin="SCRAPED_DOM",
                )
            )

        candidates, blobs = [], {}
        for scraped_image in page.images:
            # Una imagen rota/inaccesible no tumba el scraping completo.
            try:
                downloaded = await self._downloader.download(scraped_image.url)
                probe = await self._image_inspector.inspect(downloaded.content)
            except Exception:
                logger.warning("Imagen candidata descartada (no descargable/decodificable): %s",
                               scraped_image.url)
                continue
            candidates.append(
                ImageCandidate(
                    url=scraped_image.url,
                    width=probe.width,
                    height=probe.height,
                    perceptual_hash=probe.perceptual_hash,
                    section=scraped_image.section,
                )
            )
            blobs[scraped_image.url] = downloaded

        for selected in self._artifact_selection.select(candidates):  # FOR-99
            downloaded = blobs[selected.url]
            storage_ref = await self._storage.save(
                path=f"scraped/{uuid4().hex}-{downloaded.file_name}",
                content=downloaded.content,
            )
            artifacts.append(
                Artifact.create(
                    artifact_type=ArtifactType("IMAGE"),
                    storage_ref=storage_ref,
                    origin="SCRAPED_DOM_IMAGE",
                )
            )

        if not artifacts:
            raise UnsupportedUrlContentError(
                "La página no contiene texto ni imágenes analizables."
            )
        return artifacts
