"""Tests de FOR-112/FOR-133 (worst_case_dominates) y FOR-113 (weighted_average).

Dominio puro, sin mocks de infraestructura. Criterio de aceptación explícito
de FOR-112: si cualquier artifact resulta REJECTED, consolidated.verdict del
job es REJECTED y dominant_artifact apunta al artifact correcto.
"""
import pytest

from app.domain.services.consolidation_service import (
    ConsolidationService,
    ScoredArtifact,
)


def test_worst_case_any_rejected_artifact_rejects_the_whole_job():
    service = ConsolidationService()
    scored = [
        ScoredArtifact("a-ok", "TEXT", 0.05),
        ScoredArtifact("a-malo", "IMAGE", 0.92),
        ScoredArtifact("a-medio", "IMAGE", 0.5),
    ]

    consolidated = service.consolidate(scored)

    assert consolidated["verdict"] == "REJECTED"
    assert consolidated["dominant_artifact"] == "a-malo"
    assert consolidated["fraud_score"] == 0.92
    assert consolidated["policy_applied"] == "worst_case_dominates"


def test_worst_case_all_clean_approves():
    service = ConsolidationService()
    scored = [ScoredArtifact("a1", "TEXT", 0.1), ScoredArtifact("a2", "IMAGE", 0.2)]

    consolidated = service.consolidate(scored)

    assert consolidated["verdict"] == "APPROVED"
    assert consolidated["dominant_artifact"] == "a2"
    assert consolidated["fraud_score"] == 0.2
    assert consolidated["risk_percentage"] == 20
    assert consolidated["authenticity_percentage"] == 80


def test_worst_case_middle_score_is_suspicious():
    consolidated = ConsolidationService().consolidate([ScoredArtifact("a", "IMAGE", 0.55)])
    assert consolidated["verdict"] == "SUSPICIOUS"


def test_weighted_average_images_weigh_more_than_text():
    service = ConsolidationService(policy="weighted_average")

    scored = [
        ScoredArtifact("foto", "IMAGE", 0.9),
        ScoredArtifact("texto", "TEXT", 0.1),
    ]

    consolidated = service.consolidate(scored)

    assert consolidated["fraud_score"] == 0.66
    assert consolidated["verdict"] == "SUSPICIOUS"
    assert consolidated["dominant_artifact"] == "foto"
    assert consolidated["policy_applied"] == "weighted_average"


def test_weighted_average_differs_from_worst_case_on_same_input():
    scored = [ScoredArtifact("foto", "IMAGE", 0.9), ScoredArtifact("texto", "TEXT", 0.1)]
    worst = ConsolidationService().consolidate(scored)
    weighted = ConsolidationService(policy="weighted_average").consolidate(scored)
    assert worst["verdict"] == "REJECTED"
    assert weighted["verdict"] != worst["verdict"]


def test_weighted_average_custom_weights():
    service = ConsolidationService(
        policy="weighted_average", type_weights={"IMAGE": 1.0, "TEXT": 0.0}
    )
    scored = [ScoredArtifact("foto", "IMAGE", 0.8), ScoredArtifact("texto", "TEXT", 0.0)]
    assert service.consolidate(scored)["fraud_score"] == 0.8


def test_invalid_policy_fails_fast():
    with pytest.raises(ValueError, match="CONSOLIDATION_POLICY"):
        ConsolidationService(policy="typo_policy")


def test_empty_artifact_list_is_rejected():
    with pytest.raises(ValueError):
        ConsolidationService().consolidate([])


def test_incomplete_low_risk_analysis_is_inconclusive_not_approved():
    consolidated = ConsolidationService().consolidate([
        ScoredArtifact("doc", "TEXT", 0.0, analysis_complete=False)
    ])
    assert consolidated["verdict"] == "INCONCLUSIVE"
    assert consolidated["authenticity_percentage"] is None
    assert consolidated["risk_percentage"] == 0
    assert consolidated["analysis_complete"] is False


def test_incomplete_analysis_does_not_hide_detected_high_risk():
    consolidated = ConsolidationService().consolidate([
        ScoredArtifact("doc", "TEXT", 0.9, analysis_complete=False)
    ])
    assert consolidated["verdict"] == "REJECTED"
