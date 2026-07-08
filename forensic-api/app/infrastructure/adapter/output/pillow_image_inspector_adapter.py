"""Adaptador de salida: PillowImageInspectorAdapter (FOR-99, ImageInspectorPort).

Mide dimensiones y calcula el aHash perceptual de 64 bits (escala de grises
8x8, bit=1 si el píxel supera el promedio). Dos imágenes iguales o casi
iguales (recompresión, resize) producen hashes a distancia de Hamming corta.
"""
import asyncio
import io

from PIL import Image

from app.domain.ports.image_inspector_port import ImageInspectorPort, ImageProbe

_HASH_SIDE = 8


class PillowImageInspectorAdapter(ImageInspectorPort):
    async def inspect(self, content: bytes) -> ImageProbe:
        return await asyncio.to_thread(self._inspect_sync, content)

    @staticmethod
    def _inspect_sync(content: bytes) -> ImageProbe:
        try:
            with Image.open(io.BytesIO(content)) as image:
                width, height = image.size
                gray = image.convert("L").resize((_HASH_SIDE, _HASH_SIDE), Image.LANCZOS)
        except Exception as exc:
            raise ValueError(f"Contenido no decodificable como imagen: {exc}") from exc

        pixels = list(gray.getdata())
        average = sum(pixels) / len(pixels)
        perceptual_hash = 0
        for index, pixel in enumerate(pixels):
            if pixel > average:
                perceptual_hash |= 1 << index

        return ImageProbe(width=width, height=height, perceptual_hash=perceptual_hash)
