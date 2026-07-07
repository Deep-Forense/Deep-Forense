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
