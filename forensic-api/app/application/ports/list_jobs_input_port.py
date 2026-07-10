"""Puerto de entrada: expone el caso de uso de historial de jobs (FOR-100)."""
from abc import ABC, abstractmethod
from typing import Optional

from app.application.dto.jobs_page import JobsPage


class ListJobsInputPort(ABC):
    @abstractmethod
    async def execute(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        verdict: Optional[str] = None,
    ) -> JobsPage:
        """Historial paginado del usuario autenticado (nunca de otros usuarios
        ni de jobs demo)."""
        ...
