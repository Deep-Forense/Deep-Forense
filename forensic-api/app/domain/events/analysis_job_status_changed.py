"""Domain Event: AnalysisJobStatusChanged (FOR-114 / HU6.4).

Se emite en cada transición válida de la máquina de estados del AnalysisJob
(PENDING -> PROCESSING -> COMPLETED/FAILED), con timestamp. Se acumula en el
aggregate y se libera con pull_domain_events(), igual que AnalysisJobCreated.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class AnalysisJobStatusChanged:
    job_id: str
    from_status: str
    to_status: str
    occurred_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.occurred_at is None:
            object.__setattr__(self, "occurred_at", datetime.now(timezone.utc))
