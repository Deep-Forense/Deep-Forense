"""Tests de FOR-114 (HU6.4) — máquina de estados y eventos del AnalysisJob.

Dominio puro: sin Mongo, sin FastAPI.
"""
import pytest

from app.domain.aggregates.analysis_job import AnalysisJob
from app.domain.entities.artifact import Artifact
from app.domain.events.analysis_job_created import AnalysisJobCreated
from app.domain.events.analysis_job_status_changed import AnalysisJobStatusChanged
from app.domain.exceptions import InvalidJobTransitionError
from app.domain.value_objects.artifact_type import ArtifactType


def _job(artifact_statuses=("PENDING",)) -> AnalysisJob:
    artifacts = [
        Artifact.create(artifact_type=ArtifactType("IMAGE"), storage_ref=f"bucket/{i}.jpg")
        for i, _ in enumerate(artifact_statuses)
    ]
    for artifact, status in zip(artifacts, artifact_statuses):
        artifact.status = status
    return AnalysisJob.create(user_id="u1", artifacts=artifacts)


def test_happy_path_transitions_emit_events_with_timestamps():
    job = _job()
    job.transition_to("PROCESSING")
    job.transition_to("COMPLETED")

    events = job.pull_domain_events()
    assert isinstance(events[0], AnalysisJobCreated)
    transitions = [e for e in events if isinstance(e, AnalysisJobStatusChanged)]
    assert [(e.from_status, e.to_status) for e in transitions] == [
        ("PENDING", "PROCESSING"),
        ("PROCESSING", "COMPLETED"),
    ]
    assert all(e.occurred_at is not None for e in events)
    assert job.completed_at is not None


def test_completed_job_cannot_go_back_to_processing():
    job = _job()
    job.transition_to("PROCESSING")
    job.transition_to("COMPLETED")

    with pytest.raises(InvalidJobTransitionError):
        job.transition_to("PROCESSING")


def test_pending_cannot_jump_straight_to_completed():
    with pytest.raises(InvalidJobTransitionError):
        _job().transition_to("COMPLETED")


def test_pull_domain_events_drains_the_queue():
    job = _job()
    job.transition_to("PROCESSING")
    assert len(job.pull_domain_events()) == 2  # created + status_changed
    assert job.pull_domain_events() == []


def test_one_failed_artifact_does_not_fail_job_if_another_completed():
    job = _job(artifact_statuses=("COMPLETED", "FAILED"))
    job.conclude_from_artifacts(consolidated={"fraud_score": 0.1})
    assert job.status == "COMPLETED"
    assert job.consolidated == {"fraud_score": 0.1}


def test_job_fails_only_when_all_artifacts_failed():
    job = _job(artifact_statuses=("FAILED", "FAILED"))
    job.conclude_from_artifacts()
    assert job.status == "FAILED"
    assert job.completed_at is not None
