"""Value Object: ImageCandidate (FOR-99 / HU3.4).

Imagen candidata extraída del scraping de una página, ya medida por
infraestructura (dimensiones + hash perceptual). El dominio decide sobre
estos valores sin conocer Pillow ni HTTP.

`section`: pista de posición en el DOM que asigna el scraper —
"main" (contenido principal), "header", "footer", "sidebar", "nav" o
"unknown" si no se pudo determinar.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ImageCandidate:
    url: str
    width: int
    height: int
    perceptual_hash: int  # aHash de 64 bits (8x8) calculado por ImageInspectorPort
    section: str = "unknown"
