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
    ela_heatmap_ref: Optional[str] = None  # solo IMAGE; storage_ref ('{bucket}/{path}') del PNG en MinIO
    document_page_count: Optional[int] = None
    document_analyzed_pages: Optional[int] = None
    document_text_layer_pages: Optional[int] = None
    document_ocr_pages: Optional[int] = None
    document_embedded_images: Optional[int] = None
    document_truncated: Optional[bool] = None
    document_consistency_score: Optional[float] = None
    document_consistency_checks: list = field(default_factory=list)
    document_visual_score: Optional[float] = None
    document_visual_evidence: list = field(default_factory=list)
    document_visual_heatmap_ref: Optional[str] = None
    pdf_structure_score: Optional[float] = None
    pdf_structure: Optional[dict] = None
    pdf_structure_flags: list = field(default_factory=list)
    ocr_available: Optional[bool] = None
    cognitive_available: Optional[bool] = None
    analysis_warnings: list = field(default_factory=list)

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
            "ela_heatmap_ref": self.ela_heatmap_ref,
            "document_page_count": self.document_page_count,
            "document_analyzed_pages": self.document_analyzed_pages,
            "document_text_layer_pages": self.document_text_layer_pages,
            "document_ocr_pages": self.document_ocr_pages,
            "document_embedded_images": self.document_embedded_images,
            "document_truncated": self.document_truncated,
            "document_consistency_score": self.document_consistency_score,
            "document_consistency_checks": self.document_consistency_checks,
            "document_visual_score": self.document_visual_score,
            "document_visual_evidence": self.document_visual_evidence,
            "document_visual_heatmap_ref": self.document_visual_heatmap_ref,
            "pdf_structure_score": self.pdf_structure_score,
            "pdf_structure": self.pdf_structure,
            "pdf_structure_flags": self.pdf_structure_flags,
            "ocr_available": self.ocr_available,
            "cognitive_available": self.cognitive_available,
            "analysis_warnings": self.analysis_warnings,
        }

    def numeric_scores(self) -> list:
        """Señales numéricas presentes (para el consolidated placeholder de Sprint 2)."""
        return [
            s
            for s in (
                self.benford_score, self.document_consistency_score, self.document_visual_score,
                self.pdf_structure_score,
                self.exif_score,
                self.ela_score, self.dct_benford_score,
            )
            if s is not None
        ]
