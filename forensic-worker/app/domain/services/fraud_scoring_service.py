"""Servicio de DOMINIO: FraudScoringService (FOR-111 / HU6.1).

Combina los scores parciales de la Capa 2 (Sprint 2) en un score de riesgo
único [0.0, 1.0] por artifact. Lógica pura: sin Mongo, sin HTTP, sin OpenCV.

Reglas:
  - Solo entran las señales numéricas PRESENTES en el analysis. Una señal
    no aplicable (p.ej. benford_applicable=false => benford_score=None,
    dct_benford_score=None) queda excluida del cálculo, no penaliza.
  - Las banderas cognitivas (ai_flags/gemini_flags, deduplicadas) aportan un
    factor que satura en FLAGS_SATURATION banderas distintas.
  - score = SIGNAL_WEIGHT * promedio(señales) + FLAGS_WEIGHT * factor_flags.
    Si no hay ninguna señal numérica (p.ej. TEXT no financiero), el score
    queda determinado solo por las banderas.
"""
from app.domain.entities.artifact_analysis import ArtifactAnalysis
from app.domain.services.image_classification_service import risk_floor_for_flags

SIGNAL_WEIGHT = 0.7
FLAGS_WEIGHT = 0.3

FLAGS_SATURATION = 3


class FraudScoringService:
    def score(self, analysis: ArtifactAnalysis) -> float:
        signals = analysis.numeric_scores()
        distinct_flags = set(analysis.ai_flags) | set(analysis.gemini_flags)
        flags_factor = min(1.0, len(distinct_flags) / FLAGS_SATURATION)
        semantic_floor = risk_floor_for_flags(list(distinct_flags))

        if not signals:

            return round(max(flags_factor, semantic_floor), 4)

        signal_mean = sum(signals) / len(signals)
        combined = SIGNAL_WEIGHT * signal_mean + FLAGS_WEIGHT * flags_factor
        return round(min(1.0, max(0.0, combined, semantic_floor)), 4)
