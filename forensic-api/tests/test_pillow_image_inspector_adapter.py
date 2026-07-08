"""Tests de FOR-99 — PillowImageInspectorAdapter (imágenes sintéticas, sin red)."""
import io

import pytest
from PIL import Image

from app.infrastructure.adapter.output.pillow_image_inspector_adapter import (
    PillowImageInspectorAdapter,
)


def _gradient_png(width, height, invert=False):
    """Gradiente horizontal suave: estable ante resize (a diferencia de un
    patrón de alta frecuencia, que cambia su aHash al escalar)."""
    image = Image.new("L", (width, height))
    pixels = image.load()
    for x in range(width):
        value = int(255 * x / width)
        if invert:
            value = 255 - value
        for y in range(height):
            pixels[x, y] = value
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


async def test_reports_dimensions():
    probe = await PillowImageInspectorAdapter().inspect(_gradient_png(320, 240))
    assert (probe.width, probe.height) == (320, 240)


async def test_same_image_at_different_sizes_has_close_hashes():
    adapter = PillowImageInspectorAdapter()
    large = await adapter.inspect(_gradient_png(400, 300))
    small = await adapter.inspect(_gradient_png(200, 150))
    distance = bin(large.perceptual_hash ^ small.perceptual_hash).count("1")
    assert distance <= 8  # mismo umbral que ArtifactSelectionService


async def test_different_images_have_distant_hashes():
    adapter = PillowImageInspectorAdapter()
    a = await adapter.inspect(_gradient_png(300, 300))
    b = await adapter.inspect(_gradient_png(300, 300, invert=True))  # gradiente invertido
    distance = bin(a.perceptual_hash ^ b.perceptual_hash).count("1")
    assert distance > 8


async def test_invalid_content_raises_value_error():
    with pytest.raises(ValueError):
        await PillowImageInspectorAdapter().inspect(b"no soy una imagen")
