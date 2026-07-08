"""DTO de entrada al caso de uso SubmitUrlAnalysisUseCase (FOR-97)."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SubmitUrlAnalysisCommand:
    user_id: Optional[str]
    url: str
