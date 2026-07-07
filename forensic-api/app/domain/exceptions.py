"""Excepciones de dominio de Forensic Analysis Context."""


class EmptyJobError(Exception):
    """Se lanza si se intenta crear un AnalysisJob sin artifacts."""


class InvalidJobTransitionError(Exception):
    """Se lanza si se intenta una transición de estado inválida."""


class JobNotFoundError(Exception):
    """Se lanza cuando se busca un job_id que no existe."""
