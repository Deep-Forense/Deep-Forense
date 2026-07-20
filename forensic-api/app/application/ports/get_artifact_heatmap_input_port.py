"""Puerto de entrada: consulta del heatmap ELA de un artifact
(GET /api/forensic/jobs/{job_id}/artifacts/{artifact_id}/ela-heatmap)."""
from abc import ABC, abstractmethod
from typing import Optional


class GetArtifactHeatmapInputPort(ABC):
    @abstractmethod
    async def execute(self, job_id: str, artifact_id: str, user_id: Optional[str]) -> Optional[bytes]:
        """Bytes del PNG, o None si el job/artifact/heatmap no existe o el
        solicitante no es el dueño del job (mismo criterio que detail_level=full)."""
        ...
