"""Tests de RF-28 (lado worker) — eventos $push en las transiciones reales.

Colección fake síncrona (el adaptador usa pymongo vía asyncio.to_thread):
sin Mongo real, mismo patrón de fakes del resto de la suite.
"""
from app.domain.entities.artifact import Artifact
from app.infrastructure.adapter.output.mongo_analysis_job_repository import (
    MongoAnalysisJobRepository,
)


class FakeCollection:
    """Captura las llamadas a update_one (filter, update) para inspección."""

    def __init__(self) -> None:
        self.updates: list = []

    def update_one(self, query, update):
        self.updates.append((query, update))

    def find_one(self, query, projection=None):
        return None


async def test_mark_processing_pushes_job_processing_event():
    collection = FakeCollection()
    repository = MongoAnalysisJobRepository(collection)

    await repository.mark_processing("job-1")

    query, update = collection.updates[0]
    assert query == {"_id": "job-1", "status": "PENDING"}
    assert update["$set"] == {"status": "PROCESSING"}
    event = update["$push"]["events"]
    assert event["type"] == "JOB_PROCESSING"
    assert event["timestamp"] is not None


async def test_complete_job_success_pushes_job_completed_event():
    collection = FakeCollection()
    repository = MongoAnalysisJobRepository(collection)

    await repository.complete_job("job-2", "COMPLETED", {"fraud_score": 0.1})

    _, update = collection.updates[0]
    assert update["$set"]["status"] == "COMPLETED"
    event = update["$push"]["events"]
    assert event["type"] == "JOB_COMPLETED"

    assert event["timestamp"] == update["$set"]["completed_at"]


async def test_complete_job_failure_pushes_job_failed_event():
    collection = FakeCollection()
    repository = MongoAnalysisJobRepository(collection)

    await repository.complete_job("job-3", "FAILED", None)

    _, update = collection.updates[0]
    assert update["$set"]["status"] == "FAILED"
    assert update["$push"]["events"]["type"] == "JOB_FAILED"


async def test_save_artifact_result_does_not_touch_events():
    collection = FakeCollection()
    repository = MongoAnalysisJobRepository(collection)
    artifact = Artifact("a1", "IMAGE", "bucket/x.jpg", status="COMPLETED")

    await repository.save_artifact_result("job-4", artifact, None)

    _, update = collection.updates[0]
    assert "$push" not in update