"""DTO de salida: JobsPage (FOR-100/RF-29).

Página del historial de jobs de un usuario, con la forma del contrato
GET /api/forensic/jobs (docs/openapi.yaml): page, page_size, total, items.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class JobsPage:
    page: int
    page_size: int
    total: int
    items: list = field(default_factory=list)
