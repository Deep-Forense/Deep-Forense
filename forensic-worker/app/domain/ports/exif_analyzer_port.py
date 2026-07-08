"""Puerto de salida: ExifAnalyzerPort (T2.M1).

Analiza metadatos EXIF de una imagen buscando inconsistencias (software de
edición, fechas alteradas, metadatos eliminados).
"""
from abc import ABC, abstractmethod


class ExifAnalyzerPort(ABC):
    @abstractmethod
    async def analyze(self, image_bytes: bytes) -> float:
        """Devuelve exif_score en [0.0, 1.0] (0 = sin señales, 1 = muy sospechoso)."""
        ...
