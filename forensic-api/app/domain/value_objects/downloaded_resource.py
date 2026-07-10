"""Value Object: DownloadedResource.

Resultado de descargar una URL directa (FOR-97 / HU3.2): el contenido binario
más los metadatos mínimos para decidir el tipo de artifact. Inmutable y sin
dependencias de framework (regla de arquitectura hexagonal).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class DownloadedResource:
    content: bytes
    content_type: str  # content-type reportado por el servidor, sin parámetros (ej. "image/png")
    file_name: str  # último segmento del path de la URL (para el storage_ref)
