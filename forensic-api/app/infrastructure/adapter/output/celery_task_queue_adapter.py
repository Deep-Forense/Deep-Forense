"""Adaptador de salida: CeleryTaskQueueAdapter (T1.M3).

Encola la tarea `process_analysis_job` en Redis para que forensic-worker
la consuma. forensic-api NO importa el código del worker: solo envía la
tarea por nombre a través del broker compartido (Celery client "ligero").
"""
from celery import Celery

from app.domain.ports.task_queue_port import TaskQueuePort


class CeleryTaskQueueAdapter(TaskQueuePort):
    def __init__(self, celery_client: Celery) -> None:
        self._celery_client = celery_client

    def enqueue_analysis(self, job_id: str) -> None:
        self._celery_client.send_task("process_analysis_job", args=[job_id])
