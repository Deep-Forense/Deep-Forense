"""Puerto de salida para inspeccionar imágenes."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ImageProbe:
    width: int
    height: int
    perceptual_hash: int


class ImageInspectorPort(ABC):
    @abstractmethod
    async def inspect(self, content: bytes) -> ImageProbe:
        """Lanza ValueError si el contenido no es una imagen decodificable."""
        ...
