"""Puerto de salida: OcrPort (T2.M4).

Extrae el texto de un artifact TEXT (PDF o imagen de documento escaneado).
"""
from abc import ABC, abstractmethod


class OcrPort(ABC):
    @abstractmethod
    async def extract_text(self, content: bytes) -> str:
        """Devuelve el texto plano extraído del contenido binario."""
        ...
