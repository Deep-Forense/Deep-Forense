"""Caso de uso: ListJobsUseCase (FOR-100 / RF-29 / HU: historial del usuario).

Lista el historial de análisis del usuario autenticado, paginado (1-based,
contrato de docs/openapi.yaml) y con filtro opcional por veredicto.

Garantía de aislamiento: el user_id llega del JWT validado (require_user_id
en el controlador), nunca de un parámetro del cliente, y el repositorio
filtra por igualdad exacta — un usuario no puede ver jobs de otro usuario ni
jobs demo (user_id=None).
"""
from typing import Optional

from app.application.dto.jobs_page import JobsPage
from app.application.ports.list_jobs_input_port import ListJobsInputPort
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort


class ListJobsUseCase(ListJobsInputPort):
    def __init__(self, repository: AnalysisJobRepositoryPort) -> None:
        self._repository = repository

    async def execute(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        verdict: Optional[str] = None,
    ) -> JobsPage:
        if not user_id:

            raise ValueError("user_id es obligatorio para listar el historial.")

        jobs, total = await self._repository.find_by_user(
            user_id=user_id, page=page, page_size=page_size, verdict=verdict
        )
        return JobsPage(page=page, page_size=page_size, total=total, items=jobs)
