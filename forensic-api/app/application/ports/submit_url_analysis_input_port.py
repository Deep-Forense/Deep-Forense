"""Puerto de entrada: expone el caso de uso de análisis por URL (FOR-97/FOR-98)."""
from abc import ABC, abstractmethod

from app.application.dto.submit_url_analysis_command import SubmitUrlAnalysisCommand
from app.domain.aggregates.analysis_job import AnalysisJob


class SubmitUrlAnalysisInputPort(ABC):
    @abstractmethod
    async def execute(self, command: SubmitUrlAnalysisCommand) -> AnalysisJob:
        """Devuelve el AnalysisJob creado (con scraping puede tener >1 artifact,
        y el controlador necesita reportar artifacts_count — contrato JobAccepted)."""
        ...
