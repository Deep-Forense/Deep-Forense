"""Test del índice de historial (FOR-100, pendiente de la revisión).

Colección fake que registra create_index: confirma las keys exactas
{user_id: 1, created_at: -1} y que llamadas repetidas (redeploy) no fallan.
"""
from app.infrastructure.adapter.output.mongo_analysis_job_repository import (
    USER_HISTORY_INDEX,
    MongoAnalysisJobRepository,
)


class FakeCollection:
    def __init__(self) -> None:
        self.created_indexes: list = []

    async def create_index(self, keys):
        # Mongo real es idempotente: mismas keys => no-op sin excepción.
        self.created_indexes.append(keys)
        return "user_id_1_created_at_-1"


async def test_ensure_indexes_creates_user_history_compound_index():
    collection = FakeCollection()
    repository = MongoAnalysisJobRepository(collection)

    await repository.ensure_indexes()

    assert collection.created_indexes == [[("user_id", 1), ("created_at", -1)]]
    assert USER_HISTORY_INDEX == [("user_id", 1), ("created_at", -1)]


async def test_ensure_indexes_is_safe_to_call_repeatedly():
    collection = FakeCollection()
    repository = MongoAnalysisJobRepository(collection)

    await repository.ensure_indexes()
    await repository.ensure_indexes()  # redeploy: no debe lanzar

    assert len(collection.created_indexes) == 2  # ambas llamadas llegan a Mongo, que las ignora
