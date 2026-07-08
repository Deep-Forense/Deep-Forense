"""Puerto de salida: TaskQueuePort.

Encola el job creado para que forensic-worker (Capa 2/3) lo procese de forma
asíncrona (Celery/Redis en producción). El dominio y la aplicación no saben
qué tecnología de colas se usa detrás de este puerto.
"""
from abc import ABC, abstractmethod


class TaskQueuePort(ABC):
    @abstractmethod
    def enqueue_analysis(self, job_id: str) -> None: ...
