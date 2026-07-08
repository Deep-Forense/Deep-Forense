"""Tests de T2.M2 — OpenCvElaAdapter (imágenes sintéticas, sin red)."""
import io

import pytest
from PIL import Image

from app.infrastructure.adapter.output.opencv_ela_adapter import OpenCvElaAdapter

_PNG_MAGIC = b"\x89PNG"


def _jpeg_bytes(quality: int = 95) -> bytes:
    image = Image.new("RGB", (128, 128))
    # Gradiente para que la recompresión tenga contenido real que comprimir.
    pixels = image.load()
    for x in range(128):
        for y in range(128):
            pixels[x, y] = (x * 2 % 256, y * 2 % 256, (x + y) % 256)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue()


async def test_returns_score_in_unit_interval_and_png_heatmap():
    result = await OpenCvElaAdapter().analyze(_jpeg_bytes())
    assert 0.0 <= result.score <= 1.0
    assert result.heatmap_png.startswith(_PNG_MAGIC)
    assert len(result.heatmap_png) > 100


async def test_invalid_image_raises():
    with pytest.raises(ValueError):
        await OpenCvElaAdapter().analyze(b"esto no es una imagen")
