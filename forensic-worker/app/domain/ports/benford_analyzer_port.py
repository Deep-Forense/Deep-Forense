"""Puerto de salida: BenfordAnalyzerPort (T2.M3).

Mide la desviación de una serie numérica respecto de la distribución de
primer dígito de la Ley de Benford. Se reutiliza para dos señales:
  - TEXT:  financial_amounts -> benford_score
  - IMAGE: coeficientes DCT  -> dct_benford_score
"""
from abc import ABC, abstractmethod
from typing import Sequence


class BenfordAnalyzerPort(ABC):
    @abstractmethod
    async def score(self, values: Sequence[float]) -> float:
        """Devuelve un score en [0.0, 1.0] (0 = sigue Benford, 1 = se desvía mucho)."""
        ...
