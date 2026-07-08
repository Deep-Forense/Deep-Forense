"""Puerto de salida: WebScraperPort (FOR-98/FOR-134 / HU3.3).

Extrae el contenido de una página HTML: texto principal + URLs de imágenes
candidatas con su pista de sección en el DOM. La implementación concreta
(Scrapfly) vive en infrastructure/adapter/output.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScrapedImage:
    url: str
    section: str = "unknown"  # main | header | footer | sidebar | nav | unknown


@dataclass(frozen=True)
class ScrapedPage:
    text: str
    images: list = field(default_factory=list)  # list[ScrapedImage], en orden de aparición


class WebScraperPort(ABC):
    @abstractmethod
    async def scrape(self, url: str) -> ScrapedPage:
        """Lanza UrlDownloadError si el scraping falla (red, API, status != 2xx)."""
        ...
