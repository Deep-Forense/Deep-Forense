"""Adaptador de salida: OpenCvElaAdapter (T2.M2, ElaAnalyzerPort).

Error Level Analysis: recomprime la imagen a JPEG con calidad fija y mide la
diferencia absoluta con la original. Las regiones editadas/pegadas
recomprimen con un nivel de error distinto al del resto de la imagen y
"brillan" en el heatmap.

score = media de la diferencia amplificada, normalizada a [0,1] con un
factor empírico. heatmap = diferencia amplificada con colormap JET (PNG).
"""
import asyncio

import cv2
import numpy as np

from app.domain.ports.ela_analyzer_port import ElaAnalyzerPort, ElaResult

_RECOMPRESSION_QUALITY = 90
_AMPLIFICATION = 15.0
# Media de diff (0-255) que ya se considera señal máxima. Empírico: imágenes
# sin editar suelen quedar < 8; ediciones locales fuertes superan 20.
_FULL_SCALE_MEAN_DIFF = 25.0


class OpenCvElaAdapter(ElaAnalyzerPort):
    async def analyze(self, image_bytes: bytes) -> ElaResult:
        return await asyncio.to_thread(self._analyze_sync, image_bytes)

    @staticmethod
    def _analyze_sync(image_bytes: bytes) -> ElaResult:
        original = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if original is None:
            raise ValueError("No se pudo decodificar la imagen para ELA.")

        ok, recompressed_bytes = cv2.imencode(
            ".jpg", original, [cv2.IMWRITE_JPEG_QUALITY, _RECOMPRESSION_QUALITY]
        )
        if not ok:
            raise ValueError("No se pudo recomprimir la imagen para ELA.")
        recompressed = cv2.imdecode(recompressed_bytes, cv2.IMREAD_COLOR)

        diff = cv2.absdiff(original, recompressed).astype(np.float32)
        amplified = np.clip(diff * _AMPLIFICATION, 0, 255).astype(np.uint8)

        mean_diff = float(diff.mean())
        score = min(1.0, mean_diff / _FULL_SCALE_MEAN_DIFF)

        gray = cv2.cvtColor(amplified, cv2.COLOR_BGR2GRAY)
        heatmap = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
        ok, heatmap_png = cv2.imencode(".png", heatmap)
        if not ok:
            raise ValueError("No se pudo codificar el heatmap ELA a PNG.")

        return ElaResult(score=round(score, 4), heatmap_png=heatmap_png.tobytes())
