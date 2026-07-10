"""Adaptador de salida: ScrapflyScraperAdapter (FOR-98/FOR-134, WebScraperPort).

Scrapea una página HTML vía la API de Scrapfly (SCRAPFLY_API_KEY, con
render_js para SPAs) y extrae:
  - texto principal (título + headings + párrafos + items de lista), y
  - URLs absolutas de imágenes candidatas con su pista de sección en el DOM
    (main/header/footer/sidebar/nav/unknown), que FOR-99 usa para priorizar.

El httpx.AsyncClient se inyecta por constructor para testear con
httpx.MockTransport sin gastar cuota real (convención de tests del proyecto).
"""
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.domain.exceptions import UrlDownloadError
from app.domain.ports.web_scraper_port import ScrapedImage, ScrapedPage, WebScraperPort

_SCRAPFLY_URL = "https://api.scrapfly.io/scrape"
_TIMEOUT_SECONDS = 90.0
_TEXT_TAGS = ("h1", "h2", "h3", "p", "li")

# Ancestro del <img> -> sección para ArtifactSelectionService.
_SECTION_BY_ANCESTOR = {
    "header": "header",
    "footer": "footer",
    "nav": "nav",
    "aside": "sidebar",
    "main": "main",
    "article": "main",
}


def _section_for(img_tag) -> str:
    for ancestor in img_tag.parents:
        section = _SECTION_BY_ANCESTOR.get(ancestor.name)
        if section is not None:
            return section
    return "unknown"


def _extract_text(soup: BeautifulSoup) -> str:
    parts = []
    if soup.title and soup.title.string:
        parts.append(soup.title.string.strip())
    for tag in soup.find_all(_TEXT_TAGS):
        text = tag.get_text(separator=" ", strip=True)
        if text:
            parts.append(text)
    return "\n".join(parts)


def _extract_images(soup: BeautifulSoup, page_url: str) -> list:
    images, seen = [], set()
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if not src or src.startswith("data:"):
            continue
        absolute = urljoin(page_url, src)
        if absolute in seen:
            continue
        seen.add(absolute)
        images.append(ScrapedImage(url=absolute, section=_section_for(img)))
    return images


class ScrapflyScraperAdapter(WebScraperPort):
    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient | None = None,
        base_url: str = _SCRAPFLY_URL,
    ) -> None:
        self._api_key = api_key
        self._client = client
        self._base_url = base_url

    async def scrape(self, url: str) -> ScrapedPage:
        params = {"key": self._api_key, "url": url, "render_js": "true"}

        client = self._client or httpx.AsyncClient(timeout=_TIMEOUT_SECONDS)
        owns_client = self._client is None
        try:
            response = await client.get(self._base_url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # No propagar str(exc): httpx incluye la URL completa de la API,
            # que lleva la SCRAPFLY_API_KEY como query param.
            raise UrlDownloadError(
                f"Scrapfly falló para {url}: HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise UrlDownloadError(
                f"Scrapfly falló para {url}: {type(exc).__name__}"
            ) from exc
        finally:
            if owns_client:
                await client.aclose()

        html = response.json().get("result", {}).get("content", "")
        soup = BeautifulSoup(html, "html.parser")
        return ScrapedPage(text=_extract_text(soup), images=_extract_images(soup, url))
