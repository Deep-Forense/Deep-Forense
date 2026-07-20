"""Servicio de DOMINIO: ConsolidationService (FOR-112/FOR-133 y FOR-113).

Capa 3: consolida los scores por artifact (FraudScoringService) en el
resultado global del job. Lógica pura: no conoce Mongo, DeepSeek ni Gemini.

Políticas (seleccionadas por CONSOLIDATION_POLICY, ver worker.py):

  - worst_case_dominates (DEFAULT, FOR-112/HU6.2): el artifact de mayor
    riesgo manda. Si cualquier artifact resulta REJECTED, el job entero es
    REJECTED y dominant_artifact apunta a ese artifact.

  - weighted_average (FOR-113/HU6.3, solo si se configura explícitamente):
    promedio ponderado por tipo de artifact — pensado para casos como
    verificación de identidad donde las fotos (IMAGE) pesan más que el texto
    circundante (TEXT). dominant_artifact = artifact de mayor contribución
    ponderada.

Los umbrales de veredicto son los mismos acordados desde Sprint 1:
  fraud_score < 0.4 => APPROVED; > 0.7 => REJECTED; en medio => SUSPICIOUS.
"""
from dataclasses import dataclass

WORST_CASE_DOMINATES = "worst_case_dominates"
WEIGHTED_AVERAGE = "weighted_average"
_VALID_POLICIES = {WORST_CASE_DOMINATES, WEIGHTED_AVERAGE}

VERDICT_APPROVED_BELOW = 0.4
VERDICT_REJECTED_ABOVE = 0.7


DEFAULT_TYPE_WEIGHTS = {"IMAGE": 0.7, "TEXT": 0.3}


def verdict_for(fraud_score: float) -> str:
    if fraud_score < VERDICT_APPROVED_BELOW:
        return "APPROVED"
    if fraud_score > VERDICT_REJECTED_ABOVE:
        return "REJECTED"
    return "SUSPICIOUS"


@dataclass(frozen=True)
class ScoredArtifact:
    """Entrada de la consolidación: un artifact COMPLETED ya puntuado."""

    artifact_id: str
    type: str
    fraud_score: float
    analysis_complete: bool = True


class ConsolidationService:
    def __init__(
        self,
        policy: str = WORST_CASE_DOMINATES,
        type_weights: dict = None,
    ) -> None:
        if policy not in _VALID_POLICIES:
            raise ValueError(
                f"CONSOLIDATION_POLICY inválida: {policy!r}. Debe ser una de {_VALID_POLICIES}"
            )
        self._policy = policy
        self._type_weights = dict(type_weights or DEFAULT_TYPE_WEIGHTS)

    def consolidate(self, scored_artifacts: list) -> dict:
        if not scored_artifacts:
            raise ValueError("No hay artifacts completados para consolidar.")

        if self._policy == WORST_CASE_DOMINATES:
            fraud_score, dominant = self._worst_case(scored_artifacts)
        else:
            fraud_score, dominant = self._weighted_average(scored_artifacts)

        fraud_score = round(fraud_score, 4)
        normal_verdict = verdict_for(fraud_score)
        incomplete = any(not artifact.analysis_complete for artifact in scored_artifacts)
        verdict = "INCONCLUSIVE" if incomplete and normal_verdict == "APPROVED" else normal_verdict
        return {
            "fraud_score": fraud_score,
            "authenticity_percentage": None if verdict == "INCONCLUSIVE" else round((1 - fraud_score) * 100),
            "risk_percentage": round(fraud_score * 100),
            "verdict": verdict,
            "analysis_complete": not incomplete,
            "dominant_artifact": dominant.artifact_id,
            "policy_applied": self._policy,
        }

    @staticmethod
    def _worst_case(scored: list) -> tuple:
        dominant = max(scored, key=lambda a: a.fraud_score)
        return dominant.fraud_score, dominant

    def _weighted_average(self, scored: list) -> tuple:
        weights = [self._type_weights.get(a.type, 0.5) for a in scored]
        total_weight = sum(weights)
        if total_weight == 0:

            weights = [1.0] * len(scored)
            total_weight = float(len(scored))

        fraud_score = sum(w * a.fraud_score for w, a in zip(weights, scored)) / total_weight
        dominant = max(
            zip(weights, scored), key=lambda pair: pair[0] * pair[1].fraud_score
        )[1]
        return fraud_score, dominant
