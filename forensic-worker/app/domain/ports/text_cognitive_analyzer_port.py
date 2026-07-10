"""Puerto de salida: TextCognitiveAnalyzerPort (T2.M5).

Análisis semántico del texto extraído por OCR: clasifica el tipo de
documento, detecta montos financieros y produce banderas de sospecha.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class TextCognitiveResult:
    document_type: Optional[str]  # vocabulario de BenfordApplicabilityService o "other"
    financial_amounts: list = field(default_factory=list)
    ai_flags: list = field(default_factory=list)


class TextCognitiveAnalyzerPort(ABC):
    @abstractmethod
    async def analyze(self, text: str) -> TextCognitiveResult:
        ...
