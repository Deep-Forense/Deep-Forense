"""Adaptador de salida: BenfordStatisticalAdapter (T2.M3, BenfordAnalyzerPort).

Compara la distribución del primer dígito significativo de la serie contra la
distribución teórica de Benford P(d) = log10(1 + 1/d) usando distancia de
variación total (TV = 0.5 * Σ|obs - esp|, acotada en [0,1]).

score = min(1, TV / _FULL_SCALE_TV): datos naturales suelen dar TV < 0.05;
series fabricadas/manipuladas superan 0.15 con facilidad.
"""
import math
from typing import Sequence

from app.domain.ports.benford_analyzer_port import BenfordAnalyzerPort

_BENFORD_EXPECTED = {d: math.log10(1 + 1 / d) for d in range(1, 10)}
_FULL_SCALE_TV = 0.30
_MIN_SAMPLE = 5


def _first_significant_digit(value: float) -> int:
    value = abs(value)
    if value == 0 or math.isnan(value) or math.isinf(value):
        return 0
    while value < 1:
        value *= 10
    while value >= 10:
        value /= 10
    return int(value)


class BenfordStatisticalAdapter(BenfordAnalyzerPort):
    async def score(self, values: Sequence[float]) -> float:
        digits = [d for d in (_first_significant_digit(v) for v in values) if 1 <= d <= 9]
        if len(digits) < _MIN_SAMPLE:
            raise ValueError(
                f"Serie insuficiente para Benford: {len(digits)} valores útiles (mínimo {_MIN_SAMPLE})."
            )

        total = len(digits)
        observed = {d: digits.count(d) / total for d in range(1, 10)}
        tv_distance = 0.5 * sum(
            abs(observed[d] - _BENFORD_EXPECTED[d]) for d in range(1, 10)
        )
        return round(min(1.0, tv_distance / _FULL_SCALE_TV), 4)
