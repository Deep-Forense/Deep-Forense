"""Caso de uso: SubmitAnalysisUseCase.

Orquesta la creación de un AnalysisJob y el encolado para la Capa 2/3.
No conoce FastAPI, Mongo, MinIO ni Celery directamente: solo conoce los
puertos de salida que recibe inyectados (inversión de dependencias).
"""
from app.application.dto.submit_analysis_command import SubmitAnalysisCommand
from app.application.ports.submit_analysis_input_port import SubmitAnalysisInputPort
from app.domain.aggregates.analysis_job import AnalysisJob
from app.domain.entities.artifact import Artifact
from app.domain.ports.analysis_job_repository_port import AnalysisJobRepositoryPort
from app.domain.ports.storage_port import StoragePort
from app.domain.ports.task_queue_port import TaskQueuePort
from app.domain.value_objects.artifact_type import ArtifactType
from uuid import uuid4


class SubmitAnalysisUseCase(SubmitAnalysisInputPort):
    def __init__(
        self,
        repository: AnalysisJobRepositoryPort,
        storage: StoragePort,
        task_queue: TaskQueuePort,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._task_queue = task_queue

    async def execute(self, command: SubmitAnalysisCommand) -> str:
        artifact_type = ArtifactType(command.artifact_type)

        # T1.M2: el archivo se guarda en MinIO ANTES de encolar la tarea.
        storage_ref = await self._storage.save(
            path=f"uploads/{uuid4().hex}-{command.file_name}",
            content=command.file_bytes,
        )
        artifact = Artifact.create(artifact_type=artifact_type, storage_ref=storage_ref)
        job = AnalysisJob.create(user_id=command.user_id, artifacts=[artifact])

        # T1.M1: se persiste el job en Mongo con status PENDING y >=1 artifact.
        await self._repository.save(job)

        # T1.M3: se encola en Redis para que forensic-worker la consuma.
        self._task_queue.enqueue_analysis(job.job_id)

        # En producción: publicar job.pull_domain_events() a un event bus.

        return job.job_id
