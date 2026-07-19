"""Adaptador de salida: PillowExifAdapter (T2.M1, ExifAnalyzerPort).

Heurísticas sobre metadatos EXIF (todas señales débiles individualmente,
se suman y se recorta a [0,1]):

  +0.45 Software de edición conocido (Photoshop, GIMP, etc.) en el tag Software.
  +0.35 DateTime (fecha de modificación) distinto de DateTimeOriginal.
  Sin EXIF no suma riesgo: es común que aplicaciones y redes sociales lo
  eliminen por privacidad o durante la recompresión.
  +0.15 Hay fecha de modificación pero se eliminó la fecha original.
"""
import asyncio
import io

from PIL import Image

from app.domain.ports.exif_analyzer_port import ExifAnalyzerPort

_TAG_SOFTWARE = 0x0131
_TAG_DATETIME = 0x0132
_EXIF_IFD = 0x8769
_TAG_DATETIME_ORIGINAL = 0x9003

_EDITING_SOFTWARE_KEYWORDS = (
    "photoshop",
    "gimp",
    "lightroom",
    "affinity",
    "pixelmator",
    "canva",
    "paint.net",
    "photopea",
    "snapseed",
    "picsart",
)

_SCORE_EDITING_SOFTWARE = 0.45
_SCORE_DATETIME_MISMATCH = 0.35
_SCORE_ORIGINAL_DATE_STRIPPED = 0.15


class PillowExifAdapter(ExifAnalyzerPort):
    async def analyze(self, image_bytes: bytes) -> float:
        return await asyncio.to_thread(self._analyze_sync, image_bytes)

    @staticmethod
    def _analyze_sync(image_bytes: bytes) -> float:
        with Image.open(io.BytesIO(image_bytes)) as image:
            exif = image.getexif()

            if len(exif) == 0:
                return 0.0

            score = 0.0

            software = str(exif.get(_TAG_SOFTWARE, "")).lower()
            if any(keyword in software for keyword in _EDITING_SOFTWARE_KEYWORDS):
                score += _SCORE_EDITING_SOFTWARE

            date_time = exif.get(_TAG_DATETIME)
            try:
                exif_ifd = exif.get_ifd(_EXIF_IFD)
            except KeyError:
                exif_ifd = {}
            # DateTimeOriginal vive normalmente en el Exif IFD, pero algunos
            # escritores lo dejan en el IFD principal: se aceptan ambos.
            date_time_original = exif_ifd.get(_TAG_DATETIME_ORIGINAL) or exif.get(
                _TAG_DATETIME_ORIGINAL
            )

            if date_time and date_time_original and date_time != date_time_original:
                score += _SCORE_DATETIME_MISMATCH
            elif date_time and not date_time_original:
                score += _SCORE_ORIGINAL_DATE_STRIPPED

            return min(1.0, score)
