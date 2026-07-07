"""Caso de uso: GetJobUseCase.

Consulta el estado/resultado de un job. La decisión de detail_level
(basic vs full, según autenticación) se resuelve en el adaptador de
entrada (controlador REST), que es quien conoce el JWT de la petición.
"""
from typing import Optional

from app.application.ports.get_job_input_port import GetJobInputPort
from app.domain.aggregates.analysis_job import AnalysisJob
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort


class GetJobUseCase(GetJobInputPort):
    def __init__(self, repository: AnalysisJobRepositoryPort) -> None:
        self._repository = repository

    async def execute(self, job_id: str) -> Optional[AnalysisJob]:
        return await self._repository.find_by_id(job_id)
