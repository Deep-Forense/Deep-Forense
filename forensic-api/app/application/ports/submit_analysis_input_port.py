"""Puerto de entrada: expone el caso de uso al adaptador de entrada (controlador REST)."""
from abc import ABC, abstractmethod

from app.application.dto.submit_analysis_command import SubmitAnalysisCommand


class SubmitAnalysisInputPort(ABC):
    @abstractmethod
    async def execute(self, command: SubmitAnalysisCommand) -> str:
        """Devuelve el job_id creado."""
        ...
