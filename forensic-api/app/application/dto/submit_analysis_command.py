"""DTO de entrada al caso de uso SubmitAnalysisUseCase."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SubmitAnalysisCommand:
    user_id: Optional[str]
    file_bytes: bytes
    file_name: str
    artifact_type: str  # "TEXT" | "IMAGE", ya resuelto por la Capa 1
