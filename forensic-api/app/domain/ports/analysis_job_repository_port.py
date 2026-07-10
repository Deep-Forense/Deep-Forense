"""Puerto de salida: AnalysisJobRepositoryPort.

El dominio no sabe si esto lo implementa MongoDB, Postgres o memoria.
"""
from abc import ABC, abstractmethod
from typing import Optional

from app.domain.aggregates.analysis_job import AnalysisJob


class AnalysisJobRepositoryPort(ABC):
    @abstractmethod
    async def save(self, job: AnalysisJob) -> None: ...

    @abstractmethod
    async def find_by_id(self, job_id: str) -> Optional[AnalysisJob]: ...

    @abstractmethod
    async def find_by_user(
        self,
        user_id: str,
        page: int,
        page_size: int,
        verdict: Optional[str] = None,
    ) -> tuple:
        """Historial del usuario (FOR-100/RF-29), del más reciente al más antiguo.

        Paginación 1-based por contrato (docs/openapi.yaml, GET /api/forensic/jobs):
        se devuelven los jobs de la página `page` con `page_size` elementos.
        `verdict` filtra por consolidated.verdict si se indica.

        Devuelve (jobs: list[AnalysisJob], total: int) donde total es el número
        de jobs del usuario que cumplen el filtro (sin paginar). Solo jobs cuyo
        user_id coincide EXACTAMENTE: los jobs demo (user_id=None) nunca salen.
        """
        ...
