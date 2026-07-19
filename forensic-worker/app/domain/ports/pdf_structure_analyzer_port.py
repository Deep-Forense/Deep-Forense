"""Puerto para inspección estructural y criptográfica de documentos PDF."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PdfStructureResult:
    score: float
    flags: list[str]
    evidence: dict


class PdfStructureAnalyzerPort(ABC):
    @abstractmethod
    async def analyze(self, content: bytes) -> PdfStructureResult:
        ...
