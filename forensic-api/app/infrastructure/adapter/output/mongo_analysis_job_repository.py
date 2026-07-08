"""Adaptador de salida: MongoAnalysisJobRepository.

Traduce el Aggregate de dominio (AnalysisJob) al documento de MongoDB y
viceversa. Es la única pieza del sistema que conoce el esquema real de la
colección `analysis_jobs`.
"""
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorCollection

from app.domain.aggregates.analysis_job import AnalysisJob
from app.domain.entities.artifact import Artifact
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort
from app.domain.value_objects.artifact_type import ArtifactType


class MongoAnalysisJobRepository(AnalysisJobRepositoryPort):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

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
        }
        await self._collection.replace_one({"_id": job.job_id}, document, upsert=True)

    async def find_by_id(self, job_id: str) -> Optional[AnalysisJob]:
        doc = await self._collection.find_one({"_id": job_id})
        if doc is None:
            return None
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
        )
