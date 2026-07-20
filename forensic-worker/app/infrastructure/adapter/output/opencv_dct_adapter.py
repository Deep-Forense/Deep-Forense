"""Adaptador de salida: OpenCvDctAdapter (T2.M3, DctAnalyzerPort).

Extrae coeficientes DCT AC de bloques 8x8 (la misma transformada que usa la
compresión JPEG). En una imagen JPEG sin manipular, los primeros dígitos de
los coeficientes AC siguen la Ley de Benford; una recompresión/edición local
la distorsiona. El scoring lo hace BenfordStatisticalAdapter.

Nota: solo tiene sentido en JPEG; la aplicabilidad la decide
BenfordApplicabilityService (T2.M7), no este adaptador.
"""
import asyncio
from typing import Sequence

import cv2
import numpy as np

from app.domain.ports.dct_analyzer_port import DctAnalyzerPort

_BLOCK = 8

_MAX_ANALYSIS_SIDE = 512
_MIN_COEFFICIENT = 1e-6


class OpenCvDctAdapter(DctAnalyzerPort):
    async def extract_coefficients(self, image_bytes: bytes) -> Sequence[float]:
        return await asyncio.to_thread(self._extract_sync, image_bytes)

    @staticmethod
    def _extract_sync(image_bytes: bytes) -> Sequence[float]:
        gray = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            raise ValueError("No se pudo decodificar la imagen para DCT.")

        height, width = gray.shape
        side_y = min(height, _MAX_ANALYSIS_SIDE)
        side_x = min(width, _MAX_ANALYSIS_SIDE)
        top = (height - side_y) // 2
        left = (width - side_x) // 2
        crop = gray[top : top + side_y - side_y % _BLOCK, left : left + side_x - side_x % _BLOCK]
        if crop.shape[0] < _BLOCK or crop.shape[1] < _BLOCK:
            raise ValueError("Imagen demasiado pequeña para análisis DCT (mínimo 8x8).")

        blocks_y = crop.shape[0] // _BLOCK
        blocks_x = crop.shape[1] // _BLOCK

        blocks = (
            crop.astype(np.float32)
            .reshape(blocks_y, _BLOCK, blocks_x, _BLOCK)
            .transpose(0, 2, 1, 3)
            .reshape(-1, _BLOCK, _BLOCK)
        )

        coefficients = np.empty_like(blocks)
        for i, block in enumerate(blocks):
            coefficients[i] = cv2.dct(block)

        ac = np.abs(coefficients.reshape(len(blocks), -1)[:, 1:])
        ac = ac[ac > _MIN_COEFFICIENT]
        return ac.tolist()
