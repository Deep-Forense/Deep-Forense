"""Descarga limitada de una URL HTTP/HTTPS que debe contener una imagen."""
import ipaddress
from urllib.parse import unquote, urljoin, urlparse

import httpx

from app.domain.exceptions import UrlDownloadError
from app.domain.ports.url_downloader_port import UrlDownloaderPort
from app.domain.value_objects.downloaded_resource import DownloadedResource

_MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
_DEFAULT_TIMEOUT_SECONDS = 30.0
_MAX_REDIRECTS = 5
_REDIRECT_CODES = {301, 302, 303, 307, 308}


def _file_name_from_url(url: str) -> str:
    segment = unquote(urlparse(url).path.rsplit("/", 1)[-1])
    return segment or "imagen"


def _validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UrlDownloadError("Ingresa un enlace directo HTTP o HTTPS válido.")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise UrlDownloadError("No se permiten enlaces a servicios locales.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return
    if not address.is_global:
        raise UrlDownloadError("No se permiten enlaces a redes privadas o locales.")


class HttpxUrlDownloaderAdapter(UrlDownloaderPort):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def download(self, url: str) -> DownloadedResource:
        client = self._client or httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SECONDS)
        owns_client = self._client is None
        current_url = url
        try:
            for _ in range(_MAX_REDIRECTS + 1):
                _validate_public_url(current_url)
                async with client.stream("GET", current_url) as response:
                    if response.status_code in _REDIRECT_CODES:
                        location = response.headers.get("location")
                        if not location:
                            raise UrlDownloadError("La URL respondió con una redirección inválida.")
                        current_url = urljoin(str(response.url), location)
                        continue
                    response.raise_for_status()
                    declared = response.headers.get("content-length")
                    if declared and int(declared) > _MAX_DOWNLOAD_BYTES:
                        raise UrlDownloadError("La imagen supera el límite de 50 MB.")
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        content.extend(chunk)
                        if len(content) > _MAX_DOWNLOAD_BYTES:
                            raise UrlDownloadError("La imagen supera el límite de 50 MB.")
                    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                    return DownloadedResource(
                        content=bytes(content), content_type=content_type,
                        file_name=_file_name_from_url(str(response.url)),
                    )
            raise UrlDownloadError("La URL tiene demasiadas redirecciones.")
        except UrlDownloadError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise UrlDownloadError(
                "No se pudo obtener la imagen. Comprueba que el enlace sea directo y público, y vuelve a intentarlo."
            ) from exc
        finally:
            if owns_client:
                await client.aclose()
