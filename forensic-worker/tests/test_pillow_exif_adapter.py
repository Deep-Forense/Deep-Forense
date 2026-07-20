"""Tests de T2.M1 — PillowExifAdapter (sin APIs externas: imágenes sintéticas)."""
import io

from PIL import Image

from app.infrastructure.adapter.output.pillow_exif_adapter import PillowExifAdapter

_TAG_SOFTWARE = 0x0131
_TAG_DATETIME = 0x0132
_EXIF_IFD = 0x8769
_TAG_DATETIME_ORIGINAL = 0x9003


def _jpeg_with_exif(software=None, date_time=None, date_time_original=None) -> bytes:
    image = Image.new("RGB", (64, 64), color=(120, 30, 200))
    exif = Image.Exif()
    if software is not None:
        exif[_TAG_SOFTWARE] = software
    if date_time is not None:
        exif[_TAG_DATETIME] = date_time
    if date_time_original is not None:

        exif[_TAG_DATETIME_ORIGINAL] = date_time_original
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


def _jpeg_without_exif() -> bytes:
    image = Image.new("RGB", (64, 64), color=(0, 100, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


async def test_missing_exif_does_not_raise_risk_by_itself():
    score = await PillowExifAdapter().analyze(_jpeg_without_exif())
    assert score == 0.0


async def test_editing_software_raises_score():
    clean = await PillowExifAdapter().analyze(
        _jpeg_with_exif(software="Camera Firmware 1.0", date_time="2026:01:01 10:00:00",
                        date_time_original="2026:01:01 10:00:00")
    )
    edited = await PillowExifAdapter().analyze(
        _jpeg_with_exif(software="Adobe Photoshop 26.0", date_time="2026:01:01 10:00:00",
                        date_time_original="2026:01:01 10:00:00")
    )
    assert edited > clean
    assert edited >= 0.45


async def test_datetime_mismatch_raises_score():
    score = await PillowExifAdapter().analyze(
        _jpeg_with_exif(date_time="2026:05:05 09:00:00", date_time_original="2026:01:01 10:00:00")
    )
    assert score >= 0.35


async def test_consistent_metadata_scores_zero():
    score = await PillowExifAdapter().analyze(
        _jpeg_with_exif(software="Canon EOS", date_time="2026:01:01 10:00:00",
                        date_time_original="2026:01:01 10:00:00")
    )
    assert score == 0.0


async def test_score_is_clamped_to_unit_interval():
    score = await PillowExifAdapter().analyze(
        _jpeg_with_exif(software="GIMP 2.10", date_time="2026:05:05 09:00:00",
                        date_time_original="2026:01:01 10:00:00")
    )
    assert 0.0 <= score <= 1.0
