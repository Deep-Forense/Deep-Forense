"""
DeepForense — forensic-worker
Composition root + adaptador de entrada (Celery).

Sprint 2: pipeline forense REAL por artifact (Capa 2), reemplazando el mock
de Sprint 1. Aquí (y solo aquí) se instancian los adaptadores concretos
(Mongo, MinIO, OpenCV, Pillow, DeepSeek, Gemini) y se inyectan en
ProcessAnalysisJobUseCase — domain/ y application/ no conocen esta
configuración (regla de arquitectura hexagonal, igual que forensic-api).

La tarea Celery `process_analysis_job` es un adaptador de entrada delgado:
construye el caso de uso y lo ejecuta con asyncio.run (el pipeline es async
para procesar los artifacts de un job en paralelo — T2.M8).

Sprint 3 (Capa 3): FraudScoringService (FOR-111) + ConsolidationService
(FOR-112/113) con política configurable vía CONSOLIDATION_POLICY
(worst_case_dominates por default; weighted_average solo si se configura).
"""
import asyncio
import os

from celery import Celery
from minio import Minio
from pymongo import MongoClient

from app.application.use_cases.process_analysis_job_use_case import ProcessAnalysisJobUseCase
from app.domain.services.benford_applicability_service import BenfordApplicabilityService
from app.domain.services.consolidation_service import ConsolidationService
from app.domain.services.fraud_scoring_service import FraudScoringService
from app.infrastructure.adapter.output.benford_statistical_adapter import BenfordStatisticalAdapter
from app.infrastructure.adapter.output.deepseek_analyzer_adapter import DeepSeekAnalyzerAdapter
from app.infrastructure.adapter.output.deepseek_ocr_adapter import DeepSeekOcrAdapter
from app.infrastructure.adapter.output.gemini_vision_analyzer_adapter import (
    GeminiVisionAnalyzerAdapter,
)
from app.infrastructure.adapter.output.minio_storage_adapter import MinioStorageAdapter
from app.infrastructure.adapter.output.mongo_analysis_job_repository import (
    MongoAnalysisJobRepository,
)
from app.infrastructure.adapter.output.opencv_dct_adapter import OpenCvDctAdapter
from app.infrastructure.adapter.output.opencv_ela_adapter import OpenCvElaAdapter
from app.infrastructure.adapter.output.pillow_exif_adapter import PillowExifAdapter

# --- Configuración desde entorno (ver docker-compose.yml / .env.example) ----
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB", "deepforense_forensic")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "deepforense")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "changeme123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "deepforense-artifacts")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_OCR_DEEPINFRA_API_KEY = os.getenv("DEEPSEEK_OCR_DEEPINFRA_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
BENFORD_MIN_AMOUNT_COUNT = int(os.getenv("BENFORD_MIN_AMOUNT_COUNT", "15"))
CONSOLIDATION_POLICY = os.getenv("CONSOLIDATION_POLICY", "worst_case_dominates")

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

# Clientes de infraestructura compartidos entre tareas (conexiones pooled).
_mongo_client = MongoClient(MONGO_URI)
_jobs_collection = _mongo_client[MONGO_DB_NAME]["analysis_jobs"]
_minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)


def build_process_job_use_case() -> ProcessAnalysisJobUseCase:
    """Se construye por invocación: los adaptadores HTTP async no deben
    compartirse entre event loops distintos (cada tarea corre su asyncio.run)."""
    return ProcessAnalysisJobUseCase(
        repository=MongoAnalysisJobRepository(_jobs_collection),
        storage=MinioStorageAdapter(_minio_client, bucket=MINIO_BUCKET),
        exif_analyzer=PillowExifAdapter(),
        ela_analyzer=OpenCvElaAdapter(),
        dct_analyzer=OpenCvDctAdapter(),
        benford_analyzer=BenfordStatisticalAdapter(),
        ocr=DeepSeekOcrAdapter(api_key=DEEPSEEK_OCR_DEEPINFRA_API_KEY),
        text_analyzer=DeepSeekAnalyzerAdapter(api_key=DEEPSEEK_API_KEY),
        image_analyzer=GeminiVisionAnalyzerAdapter(
            api_key=GEMINI_API_KEY,
            model=GEMINI_MODEL,
        ),
        benford_applicability=BenfordApplicabilityService(
            min_amount_count=BENFORD_MIN_AMOUNT_COUNT
        ),
        fraud_scoring=FraudScoringService(),
        consolidation=ConsolidationService(policy=CONSOLIDATION_POLICY),
    )


@celery_app.task(name="process_analysis_job")
def process_analysis_job(job_id: str) -> dict:
    """Punto de entrada de la Capa 2/3 para un job ya creado por forensic-api."""
    use_case = build_process_job_use_case()
    return asyncio.run(use_case.execute(job_id))
