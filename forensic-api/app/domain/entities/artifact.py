"""Entity: Artifact.

Un artifact es un elemento individual dentro de un AnalysisJob (una imagen o
un bloque de texto), procesado de forma independiente por el pipeline.
"""
from dataclasses import dataclass, field
from uuid import uuid4

from app.domain.value_objects.artifact_type import ArtifactType


@dataclass
class Artifact:
    artifact_id: str
    type: ArtifactType
    storage_ref: str
    status: str = field(default="PENDING")

    @staticmethod
    def create(artifact_type: ArtifactType, storage_ref: str) -> "Artifact":
        return Artifact(artifact_id=str(uuid4()), type=artifact_type, storage_ref=storage_ref)

    def mark_failed(self) -> None:
        self.status = "FAILED"

    def mark_completed(self) -> None:
        self.status = "COMPLETED"
