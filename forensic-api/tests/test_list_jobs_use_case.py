"""Tests de FOR-100 (RF-29) — ListJobsUseCase (historial del usuario).

Repositorio fake en memoria. Test explícito: un usuario nunca ve jobs de
otro usuario ni jobs demo (user_id=None).
"""
from typing import Optional

import pytest

from app.application.use_cases.list_jobs_use_case import ListJobsUseCase
from app.domain.aggregates.analysis_job import AnalysisJob
from app.domain.entities.artifact import Artifact
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort
from app.domain.value_objects.artifact_type import ArtifactType


def _job(user_id, verdict=None, origin="UPLOAD") -> AnalysisJob:
    artifact = Artifact.create(ArtifactType("IMAGE"), "bucket/x.jpg", origin=origin)
    job = AnalysisJob.create(user_id=user_id, artifacts=[artifact])
    if verdict is not None:
        job.consolidated = {"verdict": verdict, "fraud_score": 0.5}
    return job


class FakeRepository(AnalysisJobRepositoryPort):
    """Replica el contrato de find_by_user: igualdad exacta de user_id,
    filtro por verdict, orden por created_at descendente, paginación 1-based."""

    def __init__(self, jobs: list) -> None:
        self._jobs = jobs

    async def save(self, job) -> None: ...

    async def find_by_id(self, job_id: str): ...

    async def find_by_user(
        self, user_id: str, page: int, page_size: int, verdict: Optional[str] = None
    ) -> tuple:
        matching = [j for j in self._jobs if j.user_id == user_id]
        if verdict is not None:
            matching = [j for j in matching if (j.consolidated or {}).get("verdict") == verdict]
        matching.sort(key=lambda j: j.created_at, reverse=True)
        start = (page - 1) * page_size
        return matching[start : start + page_size], len(matching)


async def test_user_only_sees_their_own_jobs_never_others_nor_demo():
    repository = FakeRepository(
        [
            _job("user-a"),
            _job("user-a"),
            _job("user-b"),  # de otro usuario
            _job(None),  # job demo, sin dueño
        ]
    )
    use_case = ListJobsUseCase(repository)

    result = await use_case.execute(user_id="user-a")

    assert result.total == 2
    assert all(job.user_id == "user-a" for job in result.items)


async def test_pagination_returns_requested_slice():
    repository = FakeRepository([_job("u1") for _ in range(7)])
    use_case = ListJobsUseCase(repository)

    page_1 = await use_case.execute(user_id="u1", page=1, page_size=3)
    page_3 = await use_case.execute(user_id="u1", page=3, page_size=3)

    assert (page_1.page, page_1.page_size, page_1.total) == (1, 3, 7)
    assert len(page_1.items) == 3
    assert len(page_3.items) == 1  # 7 = 3 + 3 + 1


async def test_verdict_filter_is_forwarded():
    repository = FakeRepository(
        [_job("u1", verdict="APPROVED"), _job("u1", verdict="REJECTED"), _job("u1")]
    )
    use_case = ListJobsUseCase(repository)

    result = await use_case.execute(user_id="u1", verdict="REJECTED")

    assert result.total == 1
    assert result.items[0].consolidated["verdict"] == "REJECTED"


async def test_empty_user_id_is_rejected():
    use_case = ListJobsUseCase(FakeRepository([_job(None)]))
    with pytest.raises(ValueError):
        await use_case.execute(user_id="")
