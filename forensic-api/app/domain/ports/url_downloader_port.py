"""Puerto de salida: UrlDownloaderPort (FOR-97 / HU3.2).

Descarga el contenido apuntado por una URL directa. La implementación
concreta (httpx) vive en infrastructure/adapter/output.
"""
from abc import ABC, abstractmethod

from app.domain.value_objects.downloaded_resource import DownloadedResource


class UrlDownloaderPort(ABC):
    @abstractmethod
    async def download(self, url: str) -> DownloadedResource:
        """Descarga la URL y devuelve contenido + metadatos.

        Lanza UrlDownloadError si la descarga falla (red, status != 2xx,
        tamaño excesivo).
        """
        ...
