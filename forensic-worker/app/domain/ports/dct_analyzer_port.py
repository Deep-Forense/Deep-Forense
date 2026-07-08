"""Puerto de salida: DctAnalyzerPort (T2.M3).

Extrae los coeficientes DCT (AC) de una imagen JPEG. Sobre esos coeficientes
se aplica luego la Ley de Benford (BenfordAnalyzerPort) para obtener
dct_benford_score. Solo tiene sentido en JPEG (compresión con pérdida);
la decisión de aplicabilidad la toma BenfordApplicabilityService.
"""
from abc import ABC, abstractmethod
from typing import Sequence


class DctAnalyzerPort(ABC):
    @abstractmethod
    async def extract_coefficients(self, image_bytes: bytes) -> Sequence[float]:
        """Coeficientes AC (valor absoluto, sin ceros) de bloques 8x8."""
        ...
