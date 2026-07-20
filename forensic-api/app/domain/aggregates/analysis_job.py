"""Aggregate root: AnalysisJob.

Reglas de negocio puras del Forensic Analysis Context. Sin imports de
FastAPI, Motor/Pydantic ni ningún framework (regla de arquitectura
hexagonal: domain/ no depende de application/ ni de infrastructure/).
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.domain.exceptions import EmptyJobError


@dataclass
class AnalysisJob:
    job_id: str
    user_id: Optional[str]
    artifacts: list
    status: str = field(default="PENDING")
    consolidated: Optional[dict] = field(default=None)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = field(default=None)
    events: list = field(default_factory=list)

    @staticmethod
    def create(user_id: Optional[str], artifacts: list) -> "AnalysisJob":
        if not artifacts:
            raise EmptyJobError("Un AnalysisJob debe crearse con al menos 1 artifact.")

        return AnalysisJob(job_id=str(uuid4()), user_id=user_id, artifacts=artifacts, status="PENDING")
