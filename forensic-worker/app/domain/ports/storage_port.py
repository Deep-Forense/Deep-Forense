"""Puerto de salida: StoragePort (vista del worker).

A diferencia de forensic-api (que solo guarda), el worker también necesita
LEER el contenido de los artifacts ya subidos, y guardar derivados
(ela_heatmap.png).
"""
from abc import ABC, abstractmethod


class StoragePort(ABC):
    @abstractmethod
    async def get(self, storage_ref: str) -> bytes:
        """Lee el contenido apuntado por un storage_ref ('{bucket}/{path}')."""
        ...

    @abstractmethod
    async def save(self, path: str, content: bytes) -> str:
        """Guarda contenido y devuelve el storage_ref resultante."""
        ...
