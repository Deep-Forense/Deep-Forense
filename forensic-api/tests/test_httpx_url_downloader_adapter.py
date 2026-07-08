"""Tests de Tarea A (FOR-97) — HttpxUrlDownloaderAdapter con httpx.MockTransport."""
import httpx
import pytest

from app.domain.exceptions import UrlDownloadError
from app.infrastructure.adapter.output.httpx_url_downloader_adapter import (
    HttpxUrlDownloaderAdapter,
)

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16


def _client(status: int = 200, content: bytes = JPEG, content_type: str = "image/jpeg"):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=content, headers={"content-type": content_type})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_downloads_and_normalizes_content_type():
    adapter = HttpxUrlDownloaderAdapter(client=_client(content_type="Image/JPEG; charset=binary"))

    resource = await adapter.download("http://x.com/media/Foto%20final.JPG")

    assert resource.content == JPEG
    assert resource.content_type == "image/jpeg"
    assert resource.file_name == "Foto final.JPG"


async def test_http_error_raises_url_download_error():
    adapter = HttpxUrlDownloaderAdapter(client=_client(status=404))

    with pytest.raises(UrlDownloadError):
        await adapter.download("http://x.com/no-existe.jpg")


async def test_url_without_path_segment_gets_default_file_name():
    adapter = HttpxUrlDownloaderAdapter(client=_client())

    resource = await adapter.download("http://x.com/")

    assert resource.file_name == "downloaded"
