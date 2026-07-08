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
from app.domain.events.analysis_job_status_changed import AnalysisJobStatusChanged
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
        """FOR-114: máquina de estados PENDING -> PROCESSING -> COMPLETED/FAILED
        (nunca hacia atrás). Cada transición válida registra un evento con
        timestamp, recuperable vía pull_domain_events()."""
        allowed = _VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidJobTransitionError(f"Transición inválida: {self.status} -> {new_status}")
        previous_status = self.status
        self.status = new_status
        if new_status in ("COMPLETED", "FAILED"):
            self.completed_at = datetime.now(timezone.utc)
        self._domain_events.append(
            AnalysisJobStatusChanged(
                job_id=self.job_id, from_status=previous_status, to_status=new_status
            )
        )

    def complete_with(self, consolidated: dict) -> None:
        """Usado por forensic-worker (Capa 2/3) al terminar el pipeline (mock o real)."""
        self.transition_to("PROCESSING") if self.status == "PENDING" else None
        self.consolidated = consolidated
        self.transition_to("COMPLETED")

    def conclude_from_artifacts(self, consolidated: Optional[dict] = None) -> None:
        """FOR-114: un artifact FAILED no tumba el job — el job termina COMPLETED
        si al menos un artifact completó su análisis, y FAILED solo si todos
        fallaron. (forensic-worker aplica esta misma regla en su use case.)"""
        if self.status == "PENDING":
            self.transition_to("PROCESSING")
        any_completed = any(a.status == "COMPLETED" for a in self.artifacts)
        if any_completed:
            self.consolidated = consolidated
            self.transition_to("COMPLETED")
        else:
            self.transition_to("FAILED")

    def pull_domain_events(self) -> list:
        events, self._domain_events = self._domain_events, []
        return events
