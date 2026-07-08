"""Adaptador de salida: MongoAnalysisJobRepository (vista del worker).

Única pieza del worker que conoce el esquema real de `analysis_jobs`
(el mismo que escribe forensic-api). pymongo es síncrono: las operaciones
son actualizaciones puntuales y rápidas, se ejecutan en un thread para no
bloquear el event loop del pipeline (asyncio.to_thread).
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional

from pymongo.collection import Collection

from app.domain.entities.artifact import Artifact
from app.domain.entities.artifact_analysis import ArtifactAnalysis
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort


class MongoAnalysisJobRepository(AnalysisJobRepositoryPort):
    def __init__(self, collection: Collection) -> None:
        self._collection = collection

    async def get_job_status(self, job_id: str) -> Optional[str]:
        doc = await asyncio.to_thread(
            self._collection.find_one, {"_id": job_id}, {"status": 1}
        )
        return doc["status"] if doc else None

    async def get_artifacts(self, job_id: str) -> list:
        doc = await asyncio.to_thread(
            self._collection.find_one, {"_id": job_id}, {"artifacts": 1}
        )
        if doc is None:
            return []
        return [
            Artifact(
                artifact_id=a["artifact_id"],
                type=a["type"],
                storage_ref=a["storage_ref"],
                status=a.get("status", "PENDING"),
            )
            for a in doc.get("artifacts", [])
        ]

    async def mark_processing(self, job_id: str) -> None:
        await asyncio.to_thread(
            self._collection.update_one,
            {"_id": job_id, "status": "PENDING"},
            {"$set": {"status": "PROCESSING"}},
        )

    async def save_artifact_result(
        self, job_id: str, artifact: Artifact, analysis: Optional[ArtifactAnalysis]
    ) -> None:
        update = {"artifacts.$.status": artifact.status}
        if analysis is not None:
            update["artifacts.$.analysis"] = analysis.to_dict()
        await asyncio.to_thread(
            self._collection.update_one,
            {"_id": job_id, "artifacts.artifact_id": artifact.artifact_id},
            {"$set": update},
        )

    async def complete_job(self, job_id: str, status: str, consolidated: Optional[dict]) -> None:
        await asyncio.to_thread(
            self._collection.update_one,
            {"_id": job_id},
            {
                "$set": {
                    "status": status,
                    "consolidated": consolidated,
                    "completed_at": datetime.now(timezone.utc),
                }
            },
        )
