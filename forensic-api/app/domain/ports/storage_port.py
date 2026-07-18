"""Puerto de salida: StoragePort.

Guarda el contenido binario de un artifact (MinIO en producción).
"""
from abc import ABC, abstractmethod


class StoragePort(ABC):
    @abstractmethod
    async def save(self, path: str, content: bytes) -> str:
        """Devuelve la referencia de almacenamiento (storage_ref)."""
        ...

    async def get(self, path: str) -> bytes:
        """Lee un objeto privado por su ruta dentro del bucket."""
        raise NotImplementedError
