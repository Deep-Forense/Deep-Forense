"""Adaptador de salida: HttpxUrlDownloaderAdapter (FOR-97).

Descarga URLs directas a imagen/PDF con httpx. El cliente se inyecta por
constructor para poder testear con httpx.MockTransport sin tocar la red.
"""
from urllib.parse import unquote, urlparse

import httpx

from app.domain.exceptions import UrlDownloadError
from app.domain.ports.url_downloader_port import UrlDownloaderPort
from app.domain.value_objects.downloaded_resource import DownloadedResource

_MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # mismo orden que un upload razonable
_DEFAULT_TIMEOUT_SECONDS = 30.0


def _file_name_from_url(url: str) -> str:
    segment = unquote(urlparse(url).path.rsplit("/", 1)[-1])
    return segment or "downloaded"


class HttpxUrlDownloaderAdapter(UrlDownloaderPort):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def download(self, url: str) -> DownloadedResource:
        client = self._client or httpx.AsyncClient(
            follow_redirects=True, timeout=_DEFAULT_TIMEOUT_SECONDS
        )
        owns_client = self._client is None
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise UrlDownloadError(f"No se pudo descargar la URL: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

        if len(response.content) > _MAX_DOWNLOAD_BYTES:
            raise UrlDownloadError(
                f"El contenido excede el máximo permitido ({_MAX_DOWNLOAD_BYTES} bytes)."
            )

        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        return DownloadedResource(
            content=response.content,
            content_type=content_type,
            file_name=_file_name_from_url(url),
        )
