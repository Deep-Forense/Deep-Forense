"""
DeepForense — forensic-api
Composition root: aquí (y solo aquí) se instancian los adaptadores concretos
(Mongo, MinIO, Celery) y se inyectan en los casos de uso. domain/ y
application/ no conocen esta configuración (regla de arquitectura hexagonal).
"""
import os

from celery import Celery
from fastapi import FastAPI
from minio import Minio
from motor.motor_asyncio import AsyncIOMotorClient

from app.application.ports.get_artifact_heatmap_input_port import GetArtifactHeatmapInputPort
from app.application.ports.get_job_input_port import GetJobInputPort
from app.application.ports.list_jobs_input_port import ListJobsInputPort
from app.application.ports.submit_analysis_input_port import SubmitAnalysisInputPort
from app.application.ports.submit_url_analysis_input_port import SubmitUrlAnalysisInputPort
from app.application.use_cases.get_artifact_heatmap_use_case import GetArtifactHeatmapUseCase
from app.application.use_cases.get_job_use_case import GetJobUseCase
from app.application.use_cases.list_jobs_use_case import ListJobsUseCase
from app.application.use_cases.submit_analysis_use_case import SubmitAnalysisUseCase
from app.application.use_cases.submit_url_analysis_use_case import SubmitUrlAnalysisUseCase
from app.infrastructure.adapter.input.rest.analysis_controller import router as analysis_router
from app.infrastructure.adapter.output.celery_task_queue_adapter import CeleryTaskQueueAdapter
from app.infrastructure.adapter.output.httpx_url_downloader_adapter import HttpxUrlDownloaderAdapter
from app.infrastructure.adapter.output.minio_storage_adapter import MinioStorageAdapter
from app.infrastructure.adapter.output.mongo_analysis_job_repository import MongoAnalysisJobRepository
from app.infrastructure.adapter.output.pillow_image_inspector_adapter import PillowImageInspectorAdapter


MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB", "deepforense_forensic")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "deepforense")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "changeme123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "deepforense-artifacts")

ROOT_PATH = os.getenv("ROOT_PATH", "")


mongo_client = AsyncIOMotorClient(MONGO_URI)
analysis_jobs_collection = mongo_client[MONGO_DB_NAME]["analysis_jobs"]
repository = MongoAnalysisJobRepository(analysis_jobs_collection)

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)
storage = MinioStorageAdapter(minio_client, bucket=MINIO_BUCKET)

celery_client = Celery("forensic_api_producer", broker=REDIS_URL, backend=REDIS_URL)
task_queue = CeleryTaskQueueAdapter(celery_client)


submit_analysis_use_case = SubmitAnalysisUseCase(repository=repository, storage=storage, task_queue=task_queue)
url_downloader = HttpxUrlDownloaderAdapter()
submit_url_analysis_use_case = SubmitUrlAnalysisUseCase(
    repository=repository,
    storage=storage,
    task_queue=task_queue,
    downloader=url_downloader,
    image_inspector=PillowImageInspectorAdapter(),
)
get_job_use_case = GetJobUseCase(repository=repository)
list_jobs_use_case = ListJobsUseCase(repository=repository)
get_artifact_heatmap_use_case = GetArtifactHeatmapUseCase(repository=repository, storage=storage)


app = FastAPI(
    title="DeepForense — forensic-api",
    version="0.1.0",
    description="Capa 1 (Ingesta y Extracción) del pipeline forense.",
    root_path=ROOT_PATH,
)

app.dependency_overrides[SubmitAnalysisInputPort] = lambda: submit_analysis_use_case
app.dependency_overrides[SubmitUrlAnalysisInputPort] = lambda: submit_url_analysis_use_case
app.dependency_overrides[GetJobInputPort] = lambda: get_job_use_case
app.dependency_overrides[ListJobsInputPort] = lambda: list_jobs_use_case
app.dependency_overrides[GetArtifactHeatmapInputPort] = lambda: get_artifact_heatmap_use_case


@app.on_event("startup")
async def ensure_mongo_indexes():

    await repository.ensure_indexes()

app.include_router(analysis_router)


@app.get("/health")
def health():
    return {"status": "ok"}
