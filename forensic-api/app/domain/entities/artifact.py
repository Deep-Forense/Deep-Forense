"""Entity: Artifact.

Un artifact es un elemento individual dentro de un AnalysisJob (una imagen o
un bloque de texto), procesado de forma independiente por el pipeline.

`origin` (FOR-98): de dónde salió el artifact — UPLOAD (archivo subido o URL
directa a imagen/PDF), SCRAPED_DOM (texto principal de una página) o
SCRAPED_DOM_IMAGE (imagen candidata del scraping). Validado con InputSource.
`analysis` lo escribe forensic-worker (Capa 2); aquí solo se transporta para
el reporte detail_level=full.
"""
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

from app.domain.value_objects.artifact_type import ArtifactType
from app.domain.value_objects.input_source import InputSource


@dataclass
class Artifact:
    artifact_id: str
    type: ArtifactType
    storage_ref: str
    status: str = field(default="PENDING")
    origin: str = field(default="UPLOAD")
    analysis: Optional[dict] = field(default=None)

    @staticmethod
    def create(
        artifact_type: ArtifactType, storage_ref: str, origin: str = "UPLOAD"
    ) -> "Artifact":
        return Artifact(
            artifact_id=str(uuid4()),
            type=artifact_type,
            storage_ref=storage_ref,
            origin=str(InputSource(origin)),
        )

    def mark_failed(self) -> None:
        self.status = "FAILED"

    def mark_completed(self) -> None:
        self.status = "COMPLETED"
