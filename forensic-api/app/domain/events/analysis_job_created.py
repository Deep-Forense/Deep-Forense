"""Domain Event: AnalysisJobCreated.

Se emite al crear el aggregate AnalysisJob. Se acumula en una lista interna
del aggregate y se libera con pull_domain_events() para que la capa de
aplicación decida cuándo publicarlo (event bus, encolar en Celery, etc.).
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class AnalysisJobCreated:
    job_id: str
    artifact_count: int
    occurred_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.occurred_at is None:
            object.__setattr__(self, "occurred_at", datetime.now(timezone.utc))
