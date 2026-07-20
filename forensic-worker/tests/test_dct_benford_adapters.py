"""Tests de T2.M3 — OpenCvDctAdapter + BenfordStatisticalAdapter (sin red)."""
import io
import math
import random

import pytest
from PIL import Image

from app.infrastructure.adapter.output.benford_statistical_adapter import (
    BenfordStatisticalAdapter,
)
from app.infrastructure.adapter.output.opencv_dct_adapter import OpenCvDctAdapter


def _jpeg_photo_like(side: int = 256) -> bytes:
    random.seed(42)
    image = Image.new("RGB", (side, side))
    pixels = image.load()
    for x in range(side):
        for y in range(side):
            base = (x * 3 + y * 5) % 200
            noise = random.randint(0, 55)
            pixels[x, y] = (base + noise, (base + noise * 2) % 256, (base * 2 + noise) % 256)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


async def test_dct_extracts_nonzero_ac_coefficients():
    coefficients = await OpenCvDctAdapter().extract_coefficients(_jpeg_photo_like())
    assert len(coefficients) > 1000
    assert all(c > 0 for c in coefficients[:100])


async def test_dct_rejects_invalid_image():
    with pytest.raises(ValueError):
        await OpenCvDctAdapter().extract_coefficients(b"no-imagen")


async def test_benford_conformant_series_scores_low():

    random.seed(7)
    values = [10 ** random.uniform(0, 5) for _ in range(5000)]
    score = await BenfordStatisticalAdapter().score(values)
    assert score < 0.2


async def test_uniform_series_scores_higher_than_benford_series():
    random.seed(7)
    benford_like = [10 ** random.uniform(0, 5) for _ in range(5000)]
    uniform = [random.uniform(500, 999) for _ in range(5000)]
    benford_score = await BenfordStatisticalAdapter().score(benford_like)
    uniform_score = await BenfordStatisticalAdapter().score(uniform)
    assert uniform_score > benford_score
    assert uniform_score > 0.5


async def test_benford_requires_minimum_sample():
    with pytest.raises(ValueError):
        await BenfordStatisticalAdapter().score([1.0, 2.0])


async def test_jpeg_dct_coefficients_follow_benford_reasonably():
    """Integración T2.M3: DCT de un JPEG 'natural' no debe desviarse en extremo."""
    coefficients = await OpenCvDctAdapter().extract_coefficients(_jpeg_photo_like())
    score = await BenfordStatisticalAdapter().score(coefficients)
    assert not math.isnan(score)
    assert score < 0.6
