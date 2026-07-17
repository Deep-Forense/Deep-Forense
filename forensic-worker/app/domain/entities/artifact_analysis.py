"""Entity/VO: ArtifactAnalysis.

Resultado de la Capa 2 para UN artifact. Los nombres de campo son el
contrato acordado por el equipo (docs/openapi.yaml, schema
ArtifactResultFull.analysis) y NO se pueden renombrar.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ArtifactAnalysis:
    document_type: Optional[str] = None  # solo TEXT
    financial_amounts: Optional[list] = None  # solo TEXT
    ai_flags: list = field(default_factory=list)  # TEXT: DeepSeek; IMAGE: Gemini
    benford_applicable: Optional[bool] = None
    benford_score: Optional[float] = None
    exif_score: Optional[float] = None  # solo IMAGE
    ela_score: Optional[float] = None  # solo IMAGE
    dct_benford_score: Optional[float] = None  # solo IMAGE
    gemini_flags: list = field(default_factory=list)  # solo IMAGE
    image_classification: Optional[str] = None  # solo IMAGE
    image_classification_message: Optional[str] = None  # solo IMAGE

    def to_dict(self) -> dict:
        return {
            "document_type": self.document_type,
            "financial_amounts": self.financial_amounts,
            "ai_flags": self.ai_flags,
            "benford_applicable": self.benford_applicable,
            "benford_score": self.benford_score,
            "exif_score": self.exif_score,
            "ela_score": self.ela_score,
            "dct_benford_score": self.dct_benford_score,
            "gemini_flags": self.gemini_flags,
            "image_classification": self.image_classification,
            "image_classification_message": self.image_classification_message,
        }

    def numeric_scores(self) -> list:
        """Señales numéricas presentes (para el consolidated placeholder de Sprint 2)."""
        return [
            s
            for s in (self.benford_score, self.exif_score, self.ela_score, self.dct_benford_score)
            if s is not None
        ]
