"""Puerto de salida: AnalysisJobRepositoryPort (vista del worker).

Operaciones de persistencia que la Capa 2/3 necesita sobre `analysis_jobs`.
El esquema Mongo real lo conoce solo el adaptador (regla hexagonal).
"""
from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.artifact import Artifact
from app.domain.entities.artifact_analysis import ArtifactAnalysis


class AnalysisJobRepositoryPort(ABC):
    @abstractmethod
    async def get_job_status(self, job_id: str) -> Optional[str]:
        """Status actual del job, o None si no existe."""
        ...

    @abstractmethod
    async def get_artifacts(self, job_id: str) -> list:
        """Artifacts (entities del worker) del job."""
        ...

    @abstractmethod
    async def mark_processing(self, job_id: str) -> None:
        ...

    @abstractmethod
    async def save_artifact_result(
        self, job_id: str, artifact: Artifact, analysis: Optional[ArtifactAnalysis]
    ) -> None:
        """Persiste status + analysis de UN artifact (analysis None si FAILED antes de producir resultados)."""
        ...

    @abstractmethod
    async def complete_job(self, job_id: str, status: str, consolidated: Optional[dict]) -> None:
        """Cierra el job (COMPLETED/FAILED) con su consolidated y completed_at."""
        ...
