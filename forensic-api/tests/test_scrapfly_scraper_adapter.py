"""Tests de FOR-98/FOR-134 — ScrapflyScraperAdapter.

La API de Scrapfly se mockea con httpx.MockTransport: los tests nunca gastan
cuota real (convención de testing del proyecto).
"""
import httpx
import pytest

from app.domain.exceptions import UrlDownloadError
from app.infrastructure.adapter.output.scrapfly_scraper_adapter import ScrapflyScraperAdapter

PAGE_HTML = """
<html>
  <head><title>Noticia de prueba</title></head>
  <body>
    <header><img src="/static/logo.png"></header>
    <nav><img src="/static/menu-icon.png"></nav>
    <main>
      <article>
        <h1>Titular principal</h1>
        <p>Primer parrafo del articulo.</p>
        <img src="https://cdn.example.com/foto-principal.jpg">
        <img src="/media/segunda-foto.jpg">
        <img src="data:image/gif;base64,R0lGOD">  <!-- inline: se ignora -->
      </article>
    </main>
    <footer><img src="/static/footer-banner.jpg"><p>Pie de pagina</p></footer>
  </body>
</html>
"""


def _client(status=200, html=PAGE_HTML, captured=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if captured is not None:
            captured.append(request)
        return httpx.Response(status, json={"result": {"content": html}})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_extracts_text_and_absolute_image_urls_with_sections():
    captured = []
    adapter = ScrapflyScraperAdapter(api_key="sf-key", client=_client(captured=captured))

    page = await adapter.scrape("https://noticia.example.com/articulo")

    assert "Noticia de prueba" in page.text
    assert "Titular principal" in page.text
    assert "Primer parrafo del articulo." in page.text

    by_url = {img.url: img.section for img in page.images}
    assert by_url["https://cdn.example.com/foto-principal.jpg"] == "main"
    assert by_url["https://noticia.example.com/media/segunda-foto.jpg"] == "main"  # relativa -> absoluta
    assert by_url["https://noticia.example.com/static/logo.png"] == "header"
    assert by_url["https://noticia.example.com/static/menu-icon.png"] == "nav"
    assert by_url["https://noticia.example.com/static/footer-banner.jpg"] == "footer"
    assert not any(u.startswith("data:") for u in by_url)  # data-URIs ignoradas

    request = captured[0]
    assert request.url.params["key"] == "sf-key"
    assert request.url.params["url"] == "https://noticia.example.com/articulo"
    assert request.url.params["render_js"] == "true"


async def test_scrapfly_http_error_raises_url_download_error():
    adapter = ScrapflyScraperAdapter(api_key="k", client=_client(status=422))

    with pytest.raises(UrlDownloadError, match="Scrapfly"):
        await adapter.scrape("https://x.com/pagina")


async def test_error_message_never_leaks_the_api_key():
    adapter = ScrapflyScraperAdapter(api_key="sf-key-super-secreta", client=_client(status=401))

    with pytest.raises(UrlDownloadError) as exc_info:
        await adapter.scrape("https://x.com/pagina")

    assert "sf-key-super-secreta" not in str(exc_info.value)
    assert "HTTP 401" in str(exc_info.value)


async def test_page_without_images_returns_empty_list():
    adapter = ScrapflyScraperAdapter(
        api_key="k", client=_client(html="<html><body><p>Solo texto.</p></body></html>")
    )

    page = await adapter.scrape("https://x.com/texto")

    assert page.images == []
    assert "Solo texto." in page.text
