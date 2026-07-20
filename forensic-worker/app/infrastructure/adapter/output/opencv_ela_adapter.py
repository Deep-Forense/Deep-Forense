"""Adaptador de salida: OpenCvElaAdapter (T2.M2, ElaAnalyzerPort).

Error Level Analysis: recomprime la imagen a JPEG con calidad fija y mide la
diferencia absoluta con la original. Las regiones editadas/pegadas
recomprimen con un nivel de error distinto al del resto de la imagen y
"brillan" en el heatmap.

score = media de la diferencia CRUDA (sin normalizar), normalizada a [0,1]
con un factor empírico — así el score es comparable entre imágenes y sigue
alimentando FraudScoringService sin cambios.

heatmap = la MISMA diferencia, pero normalizada por percentil 99 DE ESA
imagen (no con un factor de amplificación fijo) antes de aplicar el
colormap JET. Un factor fijo (ej. x15) deja invisibles las imágenes con
diff absoluto bajo (compuestos aplanados en una sola pasada JPEG, donde no
queda historia de compresión distinta entre regiones) y sobre-satura las de
diff alto. Normalizar por percentil estira el contraste a la escala propia
de cada imagen, revelando diferencias relativas reales sin inventar señal:
si el diff es uniforme (nada editado, o un compuesto sin rastro de
compresión), el resultado sigue siendo un heatmap sin una región que
resalte — la normalización no puede fabricar una estructura que no está en
los datos, solo evita aplastar la que sí está.
"""
import asyncio

import cv2
import numpy as np

from app.domain.ports.ela_analyzer_port import ElaAnalyzerPort, ElaResult

_RECOMPRESSION_QUALITY = 90
# Media de diff (0-255) que ya se considera señal máxima. Empírico: imágenes
# sin editar suelen quedar < 8; ediciones locales fuertes superan 20.
_FULL_SCALE_MEAN_DIFF = 25.0
# Percentil usado para normalizar el heatmap (no el score). 99 en vez de un
# max() crudo: un solo pixel outlier (ruido puntual de sensor/compresión) no
# debe aplastar el contraste del resto de la imagen.
_HEATMAP_PERCENTILE = 99


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
        mean_diff = float(diff.mean())
        score = min(1.0, mean_diff / _FULL_SCALE_MEAN_DIFF)

        gray_diff = diff.mean(axis=2)
        peak = float(np.percentile(gray_diff, _HEATMAP_PERCENTILE))
        normalized = np.clip(gray_diff / peak * 255, 0, 255) if peak > 0 else gray_diff
        heatmap = cv2.applyColorMap(normalized.astype(np.uint8), cv2.COLORMAP_JET)
        ok, heatmap_png = cv2.imencode(".png", heatmap)
        if not ok:
            raise ValueError("No se pudo codificar el heatmap ELA a PNG.")

        return ElaResult(score=round(score, 4), heatmap_png=heatmap_png.tobytes())
