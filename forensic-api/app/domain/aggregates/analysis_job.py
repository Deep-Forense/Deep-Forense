"""Aggregate root: AnalysisJob.

Reglas de negocio puras del Forensic Analysis Context. Sin imports de
FastAPI, Motor/Pydantic ni ningún framework (regla de arquitectura
hexagonal: domain/ no depende de application/ ni de infrastructure/).
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.domain.events.analysis_job_created import AnalysisJobCreated
from app.domain.exceptions import EmptyJobError, InvalidJobTransitionError

_VALID_TRANSITIONS = {
    "PENDING": {"PROCESSING"},
    "PROCESSING": {"COMPLETED", "FAILED"},
    "COMPLETED": set(),
    "FAILED": set(),
}


@dataclass
class AnalysisJob:
    job_id: str
    user_id: Optional[str]
    artifacts: list
    status: str = field(default="PENDING")
    consolidated: Optional[dict] = field(default=None)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = field(default=None)
    _domain_events: list = field(default_factory=list, repr=False)

    @staticmethod
    def create(user_id: Optional[str], artifacts: list) -> "AnalysisJob":
        if not artifacts:
            raise EmptyJobError("Un AnalysisJob debe crearse con al menos 1 artifact.")

        job = AnalysisJob(job_id=str(uuid4()), user_id=user_id, artifacts=artifacts, status="PENDING")
        job._domain_events.append(AnalysisJobCreated(job_id=job.job_id, artifact_count=len(artifacts)))
        return job

    def transition_to(self, new_status: str) -> None:
        allowed = _VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidJobTransitionError(f"Transición inválida: {self.status} -> {new_status}")
        self.status = new_status
        if new_status in ("COMPLETED", "FAILED"):
            self.completed_at = datetime.now(timezone.utc)

    def complete_with(self, consolidated: dict) -> None:
        """Usado por forensic-worker (Capa 2/3) al terminar el pipeline (mock o real)."""
        self.transition_to("PROCESSING") if self.status == "PENDING" else None
        self.consolidated = consolidated
        self.transition_to("COMPLETED")

    def pull_domain_events(self) -> list:
        events, self._domain_events = self._domain_events, []
        return events
