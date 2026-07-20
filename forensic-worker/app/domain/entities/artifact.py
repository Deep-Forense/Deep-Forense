"""Entity: Artifact (vista del worker).

Referencia mínima a un artifact del job que la Capa 2 debe procesar. El
esquema completo del documento Mongo lo conoce solo el adaptador de salida
(MongoAnalysisJobRepository), igual que en forensic-api.
"""
from dataclasses import dataclass


@dataclass
class Artifact:
    artifact_id: str
    type: str
    storage_ref: str
    status: str = "PENDING"

    def is_image(self) -> bool:
        return self.type == "IMAGE"

    def is_text(self) -> bool:
        return self.type == "TEXT"
