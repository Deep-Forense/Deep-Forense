"""Caso de uso: GetArtifactHeatmapUseCase.

Sirve el PNG del heatmap ELA que forensic-worker guardó en MinIO. Mismo
control de acceso que detail_level=full en GET /jobs/{job_id}: solo el
dueño del job (jobs demo no tienen dueño y nunca lo exponen).
"""
from typing import Optional

from app.application.ports.get_artifact_heatmap_input_port import GetArtifactHeatmapInputPort
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort
from app.domain.ports.storage_port import StoragePort


class GetArtifactHeatmapUseCase(GetArtifactHeatmapInputPort):
    def __init__(self, repository: AnalysisJobRepositoryPort, storage: StoragePort) -> None:
        self._repository = repository
        self._storage = storage

    async def execute(self, job_id: str, artifact_id: str, user_id: Optional[str]) -> Optional[bytes]:
        job = await self._repository.find_by_id(job_id)
        if job is None or user_id is None or job.user_id != user_id:
            return None

        artifact = next((a for a in job.artifacts if a.artifact_id == artifact_id), None)
        if artifact is None or not artifact.analysis:
            return None

        heatmap_ref = artifact.analysis.get("ela_heatmap_ref")
        if not heatmap_ref:
            return None

        return await self._storage.get(heatmap_ref)
