"""Value Object: InputSource.

Origen de un artifact dentro del job. UPLOAD para archivos subidos directamente,
SCRAPED_DOM / SCRAPED_DOM_IMAGE para contenido extraído de una URL (Sprint 3).
"""
from dataclasses import dataclass

_ALLOWED = {"UPLOAD", "DIRECT_URL", "SCRAPED_DOM", "SCRAPED_DOM_IMAGE"}


@dataclass(frozen=True)
class InputSource:
    value: str

    def __post_init__(self) -> None:
        if self.value not in _ALLOWED:
            raise ValueError(f"InputSource inválido: {self.value!r}. Debe ser uno de {_ALLOWED}")

    def __str__(self) -> str:
        return self.value
