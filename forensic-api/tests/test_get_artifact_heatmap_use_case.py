"""Tests de GetArtifactHeatmapUseCase.

Mismo control de acceso que detail_level=full: solo el dueño del job puede
leer el heatmap ELA. Repositorio y storage fakes en memoria.
"""
from typing import Optional

import pytest

from app.application.use_cases.get_artifact_heatmap_use_case import GetArtifactHeatmapUseCase
from app.domain.aggregates.analysis_job import AnalysisJob
from app.domain.entities.artifact import Artifact
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort
from app.domain.ports.storage_port import StoragePort
from app.domain.value_objects.artifact_type import ArtifactType

HEATMAP_PNG = b"\x89PNGfake"


def _job_with_image_artifact(user_id: Optional[str], heatmap_ref: Optional[str]) -> AnalysisJob:
    artifact = Artifact.create(ArtifactType("IMAGE"), "bucket/img.jpg")
    artifact.analysis = {"ela_score": 0.4, "ela_heatmap_ref": heatmap_ref} if heatmap_ref else {"ela_score": 0.4}
    job = AnalysisJob.create(user_id=user_id, artifacts=[artifact])
    return job, artifact.artifact_id


class FakeRepository(AnalysisJobRepositoryPort):
    def __init__(self, job: Optional[AnalysisJob]) -> None:
        self._job = job

    async def save(self, job) -> None: ...

    async def find_by_id(self, job_id: str):
        return self._job

    async def find_by_user(self, user_id, page, page_size, verdict=None) -> tuple:
        return [], 0


class FakeStorage(StoragePort):
    def __init__(self, blobs: dict) -> None:
        self._blobs = blobs

    async def save(self, path: str, content: bytes) -> str:
        raise NotImplementedError

    async def get(self, storage_ref: str) -> bytes:
        return self._blobs[storage_ref]


async def test_owner_gets_the_heatmap_bytes():
    job, artifact_id = _job_with_image_artifact("user-a", "bucket/jobs/1/a/ela_heatmap.png")
    use_case = GetArtifactHeatmapUseCase(
        repository=FakeRepository(job),
        storage=FakeStorage({"bucket/jobs/1/a/ela_heatmap.png": HEATMAP_PNG}),
    )

    result = await use_case.execute("job-1", artifact_id, user_id="user-a")

    assert result == HEATMAP_PNG


async def test_other_user_gets_nothing():
    job, artifact_id = _job_with_image_artifact("user-a", "bucket/jobs/1/a/ela_heatmap.png")
    use_case = GetArtifactHeatmapUseCase(
        repository=FakeRepository(job),
        storage=FakeStorage({"bucket/jobs/1/a/ela_heatmap.png": HEATMAP_PNG}),
    )

    assert await use_case.execute("job-1", artifact_id, user_id="user-b") is None


async def test_demo_job_never_exposes_its_heatmap():
    job, artifact_id = _job_with_image_artifact(None, "bucket/jobs/1/a/ela_heatmap.png")
    use_case = GetArtifactHeatmapUseCase(
        repository=FakeRepository(job),
        storage=FakeStorage({"bucket/jobs/1/a/ela_heatmap.png": HEATMAP_PNG}),
    )

    assert await use_case.execute("job-1", artifact_id, user_id=None) is None


async def test_missing_heatmap_ref_returns_none():
    job, artifact_id = _job_with_image_artifact("user-a", heatmap_ref=None)
    use_case = GetArtifactHeatmapUseCase(repository=FakeRepository(job), storage=FakeStorage({}))

    assert await use_case.execute("job-1", artifact_id, user_id="user-a") is None


async def test_unknown_job_returns_none():
    use_case = GetArtifactHeatmapUseCase(repository=FakeRepository(None), storage=FakeStorage({}))

    assert await use_case.execute("missing-job", "any-artifact", user_id="user-a") is None
