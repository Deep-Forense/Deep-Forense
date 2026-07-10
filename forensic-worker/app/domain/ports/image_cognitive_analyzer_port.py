"""Puerto de salida: ImageCognitiveAnalyzerPort (T2.M6).

Análisis visual de la imagen con un modelo multimodal: produce banderas de
manipulación/generación (gemini_flags).
"""
from abc import ABC, abstractmethod


class ImageCognitiveAnalyzerPort(ABC):
    @abstractmethod
    async def analyze(self, image_bytes: bytes) -> list:
        """Devuelve la lista de flags (strings) detectadas en la imagen."""
        ...
