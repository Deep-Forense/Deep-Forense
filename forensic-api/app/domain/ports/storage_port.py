"""Puerto de salida: StoragePort.

Guarda el contenido binario de un artifact (MinIO en producción). También
lee derivados que escribe forensic-worker (p.ej. ela_heatmap.png) para
poder servirlos de vuelta al frontend (GET .../ela-heatmap).
"""
from abc import ABC, abstractmethod


class StoragePort(ABC):
    @abstractmethod
    async def save(self, path: str, content: bytes) -> str:
        """Devuelve la referencia de almacenamiento (storage_ref)."""
        ...

    @abstractmethod
    async def get(self, storage_ref: str) -> bytes:
        """Lee el contenido apuntado por un storage_ref ('{bucket}/{path}')."""
        ...
