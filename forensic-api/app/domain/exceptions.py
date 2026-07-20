"""Excepciones de dominio de Forensic Analysis Context."""


class EmptyJobError(Exception):
    """Se lanza si se intenta crear un AnalysisJob sin artifacts."""


class UnsupportedUrlContentError(Exception):
    """Se lanza cuando la URL no contiene una imagen directa soportada."""


class UrlDownloadError(Exception):
    """Se lanza cuando la descarga de la URL falla (red, status != 2xx, tamaño)."""
