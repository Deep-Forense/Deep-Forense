"""Excepciones de dominio de Forensic Analysis Context."""


class EmptyJobError(Exception):
    """Se lanza si se intenta crear un AnalysisJob sin artifacts."""


class InvalidJobTransitionError(Exception):
    """Se lanza si se intenta una transición de estado inválida."""


class JobNotFoundError(Exception):
    """Se lanza cuando se busca un job_id que no existe."""


class UnsupportedUrlContentError(Exception):
    """Se lanza cuando la URL no apunta directo a una imagen o PDF (FOR-97).

    El caso HTML/scraping se implementa en Sprint 3 (FOR-98/T3.M1).
    """


class UrlDownloadError(Exception):
    """Se lanza cuando la descarga de la URL falla (red, status != 2xx, tamaño)."""
