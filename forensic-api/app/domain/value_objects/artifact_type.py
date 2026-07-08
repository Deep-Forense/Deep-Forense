"""Value Object: ArtifactType.

Inmutable, se autovalida en el constructor. Solo acepta "TEXT" o "IMAGE".
Sin dependencias de framework (regla de arquitectura hexagonal).
"""
from dataclasses import dataclass

_ALLOWED = {"TEXT", "IMAGE"}


@dataclass(frozen=True)
class ArtifactType:
    value: str

    def __post_init__(self) -> None:
        if self.value not in _ALLOWED:
            raise ValueError(f"ArtifactType inválido: {self.value!r}. Debe ser uno de {_ALLOWED}")

    def is_image(self) -> bool:
        return self.value == "IMAGE"

    def is_text(self) -> bool:
        return self.value == "TEXT"

    def __str__(self) -> str:
        return self.value
