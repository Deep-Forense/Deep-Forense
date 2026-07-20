"""Tests de RF-28 (lado forensic-api) — persistencia del array `events`.

Colección fake que captura los documentos escritos: sin Mongo real, mismo
patrón de fakes del resto de la suite.
"""
from app.domain.aggregates.analysis_job import AnalysisJob
from app.domain.entities.artifact import Artifact
from app.domain.value_objects.artifact_type import ArtifactType
from app.infrastructure.adapter.output.mongo_analysis_job_repository import (
    MongoAnalysisJobRepository,
)


class FakeCollection:
    def __init__(self, docs: dict = None) -> None:
        self.docs = docs or {}

    async def replace_one(self, query, document, upsert=False):
        self.docs[query["_id"]] = document

    async def find_one(self, query):
        return self.docs.get(query["_id"])


def _new_job(user_id="u1") -> AnalysisJob:
    artifact = Artifact.create(ArtifactType("IMAGE"), "bucket/x.jpg")
    return AnalysisJob.create(user_id=user_id, artifacts=[artifact])


async def test_saving_new_job_seeds_job_created_event():
    collection = FakeCollection()
    repository = MongoAnalysisJobRepository(collection)
    job = _new_job()

    await repository.save(job)

    events = collection.docs[job.job_id]["events"]
    assert len(events) == 1
    assert events[0]["type"] == "JOB_CREATED"
    assert events[0]["timestamp"] == job.created_at


async def test_find_by_id_exposes_persisted_events():
    collection = FakeCollection()
    repository = MongoAnalysisJobRepository(collection)
    job = _new_job()
    await repository.save(job)

    collection.docs[job.job_id]["events"].append(
        {"type": "JOB_COMPLETED", "timestamp": job.created_at}
    )

    loaded = await repository.find_by_id(job.job_id)

    assert [e["type"] for e in loaded.events] == ["JOB_CREATED", "JOB_COMPLETED"]


async def test_resaving_a_loaded_job_preserves_event_history():
    collection = FakeCollection()
    repository = MongoAnalysisJobRepository(collection)
    job = _new_job()
    await repository.save(job)
    collection.docs[job.job_id]["events"].append(
        {"type": "JOB_PROCESSING", "timestamp": job.created_at}
    )

    loaded = await repository.find_by_id(job.job_id)
    await repository.save(loaded)

    events = collection.docs[job.job_id]["events"]
    assert [e["type"] for e in events] == ["JOB_CREATED", "JOB_PROCESSING"]


async def test_documents_without_events_field_load_as_empty_list():
    collection = FakeCollection()
    repository = MongoAnalysisJobRepository(collection)
    job = _new_job()
    await repository.save(job)
    del collection.docs[job.job_id]["events"]

    loaded = await repository.find_by_id(job.job_id)

    assert loaded.events == []
