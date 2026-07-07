"""
DeepForense — forensic-worker
Define la app de Celery y la tarea principal `process_analysis_job`.

Sprint 1 (T1.M4): implementación MOCK — marca el job como COMPLETED con un
fraud_score fijo, sin pipeline real de IA/forense todavía. Esto valida que
la tubería completa (frontend -> Kong -> forensic-api -> Redis ->
forensic-worker -> Mongo) funciona de punta a punta.

TODO Sprint 2 (Capa 2, por artifact, en paralelo):
  - TEXT  -> OcrPort (DeepSeekOcrAdapter) -> TextCognitiveAnalyzerPort (DeepSeekAnalyzerAdapter)
  - IMAGE -> ExifAnalyzerPort, ElaAnalyzerPort, DctAnalyzerPort, ImageCognitiveAnalyzerPort (Gemini)
  - BenfordApplicabilityService -> decide si Benford aplica por artifact

TODO Sprint 3 (Capa 3, consolidación real):
  - FraudScoringService -> score parcial real por artifact
  - ConsolidationService -> aplica política worst_case_dominates (T3.M4),
    reemplazando el mock de más abajo.

Ver docs/deepforense_mvp_consolidado.md sección 8 y docs/BACKLOG.md.
"""
import os
from datetime import datetime, timezone

from celery import Celery
from pymongo import MongoClient

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB", "deepforense_forensic")

celery_app = Celery(
    "forensic_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Guayaquil",
    enable_utc=True,
)

_mongo_client = MongoClient(MONGO_URI)
_jobs_collection = _mongo_client[MONGO_DB_NAME]["analysis_jobs"]

# Fraud score mock fijo (Sprint 1). A partir de Sprint 2/3 esto lo calcula
# FraudScoringService + ConsolidationService con datos reales.
_MOCK_FRAUD_SCORE = 0.35
_MOCK_VERDICT_THRESHOLDS = {"approved_below": 0.4, "rejected_above": 0.7}


def _mock_verdict(fraud_score: float) -> str:
    if fraud_score < _MOCK_VERDICT_THRESHOLDS["approved_below"]:
        return "APPROVED"
    if fraud_score > _MOCK_VERDICT_THRESHOLDS["rejected_above"]:
        return "REJECTED"
    return "SUSPICIOUS"


@celery_app.task(name="process_analysis_job")
def process_analysis_job(job_id: str) -> dict:
    """Punto de entrada de la Capa 2/3 para un job ya creado por forensic-api."""
    job_doc = _jobs_collection.find_one({"_id": job_id})
    if job_doc is None:
        return {"job_id": job_id, "status": "JOB_NOT_FOUND"}

    if job_doc["status"] not in ("PENDING", "PROCESSING"):
        # Ya procesado (idempotencia ante reintentos de Celery).
        return {"job_id": job_id, "status": job_doc["status"]}

    artifacts = job_doc.get("artifacts", [])
    for artifact in artifacts:
        artifact["status"] = "COMPLETED"  # mock: Sprint 2 marcará FAILED si el pipeline real falla

    fraud_score = _MOCK_FRAUD_SCORE
    consolidated = {
        "fraud_score": fraud_score,
        "authenticity_percentage": round((1 - fraud_score) * 100),
        "risk_percentage": round(fraud_score * 100),
        "verdict": _mock_verdict(fraud_score),
        "dominant_artifact": artifacts[0]["artifact_id"] if artifacts else None,
        "policy_applied": "mock_fixed_score",  # T3.M4 reemplaza por "worst_case_dominates"
    }

    _jobs_collection.update_one(
        {"_id": job_id},
        {
            "$set": {
                "status": "COMPLETED",
                "artifacts": artifacts,
                "consolidated": consolidated,
                "completed_at": datetime.now(timezone.utc),
            }
        },
    )

    return {"job_id": job_id, "status": "COMPLETED", "consolidated": consolidated}
