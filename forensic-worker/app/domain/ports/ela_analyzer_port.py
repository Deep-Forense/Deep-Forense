"""Puerto de salida: ElaAnalyzerPort (T2.M2).

Error Level Analysis: recomprime la imagen y mide diferencias de nivel de
error por región (zonas editadas recomprimen distinto). Devuelve además el
heatmap PNG para persistirlo en MinIO (lo guarda el caso de uso, no este puerto).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ElaResult:
    score: float
    heatmap_png: bytes


class ElaAnalyzerPort(ABC):
    @abstractmethod
    async def analyze(self, image_bytes: bytes) -> ElaResult:
        ...
