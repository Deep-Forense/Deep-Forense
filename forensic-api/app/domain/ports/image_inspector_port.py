"""Puerto de salida: ImageInspectorPort (FOR-99).

Mide una imagen (dimensiones + hash perceptual) para que
ArtifactSelectionService pueda decidir con lógica pura. La implementación
(Pillow) vive en infrastructure/adapter/output.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ImageProbe:
    width: int
    height: int
    perceptual_hash: int  # aHash 64 bits


class ImageInspectorPort(ABC):
    @abstractmethod
    async def inspect(self, content: bytes) -> ImageProbe:
        """Lanza ValueError si el contenido no es una imagen decodificable."""
        ...
