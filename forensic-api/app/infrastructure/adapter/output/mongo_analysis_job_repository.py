"""Adaptador de salida: MongoAnalysisJobRepository.

Traduce el Aggregate de dominio (AnalysisJob) al documento de MongoDB y
viceversa. Es la única pieza del sistema (lado forensic-api) que conoce el
esquema real de la colección `analysis_jobs`.

RF-28: cada documento embebe un array `events` con las transiciones del job
({"type": "JOB_<ESTADO>", "timestamp": ...}, esquema de
docs/deepforense_mvp_consolidado.md sección 6.2). Aquí se siembra JOB_CREATED
al crear; los eventos de PROCESSING/COMPLETED/FAILED los agrega el repositorio
del worker (quien ejecuta esas transiciones) vía $push.
"""
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorCollection

from app.domain.aggregates.analysis_job import AnalysisJob
from app.domain.entities.artifact import Artifact
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort
from app.domain.value_objects.artifact_type import ArtifactType


def _to_aggregate(doc: dict) -> AnalysisJob:
    artifacts = [
        Artifact(
            artifact_id=a["artifact_id"],
            type=ArtifactType(a["type"]),
            storage_ref=a["storage_ref"],
            status=a["status"],
            # Documentos previos a FOR-98 no traen origin/analysis.
            origin=a.get("origin", "UPLOAD"),
            analysis=a.get("analysis"),
        )
        for a in doc["artifacts"]
    ]
    return AnalysisJob(
        job_id=doc["_id"],
        user_id=doc["user_id"],
        artifacts=artifacts,
        status=doc["status"],
        consolidated=doc.get("consolidated"),
        created_at=doc["created_at"],
        completed_at=doc.get("completed_at"),
        events=doc.get("events", []),  # RF-28; documentos previos no lo traen
    )


# Índice compuesto para find_by_user (FOR-100): filtro por user_id + orden
# por created_at descendente. Sin él, cada GET /jobs es un collection scan.
USER_HISTORY_INDEX = [("user_id", 1), ("created_at", -1)]


class MongoAnalysisJobRepository(AnalysisJobRepositoryPort):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    async def ensure_indexes(self) -> None:
        """Crea los índices de la colección. Idempotente por diseño de Mongo:
        si el índice ya existe con las mismas keys (p.ej. en un redeploy),
        create_index no hace nada y no lanza. Se invoca desde el startup de
        FastAPI (main.py)."""
        await self._collection.create_index(USER_HISTORY_INDEX)

    async def save(self, job: AnalysisJob) -> None:
        document = {
            "_id": job.job_id,
            "user_id": job.user_id,
            "status": job.status,
            "consolidated": job.consolidated,
            "artifacts": [
                {
                    "artifact_id": a.artifact_id,
                    "type": str(a.type),
                    "storage_ref": a.storage_ref,
                    "status": a.status,
                    "origin": a.origin,
                    "analysis": a.analysis,
                }
                for a in job.artifacts
            ],
            "created_at": job.created_at,
            "completed_at": job.completed_at,
            # RF-28: un job recién creado (events vacío) siembra JOB_CREATED;
            # si el aggregate ya traía historial (releído de Mongo), se preserva.
            "events": job.events
            or [{"type": "JOB_CREATED", "timestamp": job.created_at}],
        }
        await self._collection.replace_one({"_id": job.job_id}, document, upsert=True)

    async def find_by_id(self, job_id: str) -> Optional[AnalysisJob]:
        doc = await self._collection.find_one({"_id": job_id})
        if doc is None:
            return None
        return _to_aggregate(doc)

    async def find_by_user(
        self,
        user_id: str,
        page: int,
        page_size: int,
        verdict: Optional[str] = None,
    ) -> tuple:
        query = {"user_id": user_id}
        if verdict is not None:
            query["consolidated.verdict"] = verdict

        total = await self._collection.count_documents(query)
        cursor = (
            self._collection.find(query)
            .sort("created_at", -1)  # más reciente primero
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        jobs = [_to_aggregate(doc) async for doc in cursor]
        return jobs, total
