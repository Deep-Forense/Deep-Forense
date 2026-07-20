"""Servicio de DOMINIO: BenfordApplicabilityService (T2.M7).

Decide si la Ley de Benford aplica a un artifact. Lógica pura: sin OpenCV,
sin HTTP, sin Mongo — solo reglas de negocio sobre datos ya extraídos.

Reglas (BACKLOG.md T2.M7):
  - TEXT:  aplica solo si document_type es financiero Y hay al menos
           `min_amount_count` montos detectados (BENFORD_MIN_AMOUNT_COUNT).
           Un texto no financiero NUNCA produce benford_score.
  - IMAGE: aplica solo si el formato es JPEG (compresión con pérdida:
           los coeficientes DCT siguen Benford en imágenes no manipuladas).
"""
from typing import Optional, Sequence

DEFAULT_MIN_AMOUNT_COUNT = 30
_MIN_MAGNITUDE_RATIO = 100.0
_MIN_UNIQUE_RATIO = 0.5


FINANCIAL_DOCUMENT_TYPES = frozenset(
    {
        "invoice",
        "receipt",
        "bank_statement",
        "financial_report",
        "budget",
        "payroll",
        "tax_document",
        "purchase_order",
    }
)

_JPEG_MAGIC = b"\xff\xd8\xff"


class BenfordApplicabilityService:
    def __init__(self, min_amount_count: int = DEFAULT_MIN_AMOUNT_COUNT) -> None:
        if min_amount_count < 1:
            raise ValueError("min_amount_count debe ser >= 1")
        self._min_amount_count = min_amount_count

    def applies_to_text(
        self,
        document_type: Optional[str],
        financial_amounts: Optional[Sequence[float]],
    ) -> bool:
        if document_type is None or document_type.lower() not in FINANCIAL_DOCUMENT_TYPES:
            return False
        if financial_amounts is None:
            return False
        usable = [abs(float(value)) for value in financial_amounts if float(value) != 0]
        if len(usable) < self._min_amount_count:
            return False
        if max(usable) / min(usable) < _MIN_MAGNITUDE_RATIO:
            return False
        if len(set(usable)) / len(usable) < _MIN_UNIQUE_RATIO:
            return False
        return True

    def applies_to_image(self, content: bytes) -> bool:
        return self.is_jpeg(content)

    @staticmethod
    def is_jpeg(content: bytes) -> bool:
        return content.startswith(_JPEG_MAGIC)
