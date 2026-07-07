"""Puerto de entrada: consulta de estado/resultado de un job (GET /api/forensic/jobs/{id})."""
from abc import ABC, abstractmethod
from typing import Optional

from app.domain.aggregates.analysis_job import AnalysisJob


class GetJobInputPort(ABC):
    @abstractmethod
    async def execute(self, job_id: str) -> Optional[AnalysisJob]: ...
