"""Puerto de entrada: expone el caso de uso de análisis por URL (FOR-97)."""
from abc import ABC, abstractmethod

from app.application.dto.submit_url_analysis_command import SubmitUrlAnalysisCommand


class SubmitUrlAnalysisInputPort(ABC):
    @abstractmethod
    async def execute(self, command: SubmitUrlAnalysisCommand) -> str:
        """Devuelve el job_id creado."""
        ...
