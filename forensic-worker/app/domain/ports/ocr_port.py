"""Puerto de salida: OcrPort (T2.M4).

Extrae el texto de un artifact TEXT (PDF o imagen de documento escaneado).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddedImage:
    content: bytes
    page_number: int
    width: int
    height: int


@dataclass(frozen=True)
class OcrExtraction:
    text: str
    page_count: int | None = None
    analyzed_pages: int | None = None
    text_layer_pages: int = 0
    ocr_pages: int = 0
    embedded_images: int = 0
    truncated: bool = False
    visual_images: tuple[EmbeddedImage, ...] = ()
    warnings: tuple[str, ...] = ()


class OcrPort(ABC):
    @abstractmethod
    async def extract_text(self, content: bytes) -> str:
        """Devuelve el texto plano extraído del contenido binario."""
        ...

    async def extract_with_metadata(self, content: bytes) -> OcrExtraction:
        return OcrExtraction(text=await self.extract_text(content))
