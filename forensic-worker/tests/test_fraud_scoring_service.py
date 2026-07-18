"""Tests de FOR-111 (HU6.1) — FraudScoringService (dominio puro, sin mocks)."""
from app.domain.entities.artifact_analysis import ArtifactAnalysis
from app.domain.services.fraud_scoring_service import FraudScoringService

service = FraudScoringService()


def test_clean_artifact_scores_zero():
    analysis = ArtifactAnalysis(exif_score=0.0, ela_score=0.0, benford_applicable=False)
    assert service.score(analysis) == 0.0


def test_all_signals_high_scores_near_one():
    analysis = ArtifactAnalysis(
        exif_score=1.0,
        ela_score=1.0,
        dct_benford_score=1.0,
        benford_applicable=True,
        ai_flags=["a", "b", "c"],
        gemini_flags=["a", "b", "c"],
    )
    assert service.score(analysis) == 1.0


def test_non_applicable_benford_is_excluded_not_penalized():
    # Mismas señales, una con benford aplicable (score alto) y otra sin él:
    with_benford = ArtifactAnalysis(
        exif_score=0.2, ela_score=0.2, benford_applicable=True, dct_benford_score=1.0
    )
    without_benford = ArtifactAnalysis(
        exif_score=0.2, ela_score=0.2, benford_applicable=False, dct_benford_score=None
    )
    assert service.score(without_benford) < service.score(with_benford)
    # sin benford: media de (0.2, 0.2) * 0.7 = 0.14 — el None no arrastra el score
    assert service.score(without_benford) == round(0.7 * 0.2, 4)


def test_text_without_signals_is_driven_by_flags_only():
    no_flags = ArtifactAnalysis(document_type="letter", benford_applicable=False)
    some_flags = ArtifactAnalysis(
        document_type="letter", benford_applicable=False, ai_flags=["f1", "f2"]
    )
    saturated = ArtifactAnalysis(
        document_type="letter", benford_applicable=False, ai_flags=["f1", "f2", "f3", "f4"]
    )
    assert service.score(no_flags) == 0.0
    assert 0.0 < service.score(some_flags) < 1.0
    assert service.score(saturated) == 1.0  # satura en FLAGS_SATURATION


def test_duplicated_flags_between_ai_and_gemini_count_once():
    # En IMAGE, ai_flags == gemini_flags (mismo origen Gemini): no debe contar doble.
    analysis = ArtifactAnalysis(
        exif_score=0.0,
        ela_score=0.0,
        ai_flags=["cloned_region"],
        gemini_flags=["cloned_region"],
    )
    expected = 0.4  # edición/composición implica como mínimo revisión
    assert service.score(analysis) == expected


def test_score_is_always_in_unit_interval():
    extreme = ArtifactAnalysis(
        exif_score=1.0, ela_score=1.0, ai_flags=[f"f{i}" for i in range(20)]
    )
    assert 0.0 <= service.score(extreme) <= 1.0


def test_ai_generation_flag_imposes_high_risk_floor():
    analysis = ArtifactAnalysis(exif_score=0.0, ela_score=0.0,
        ai_flags=["ai_generation_artifacts"], gemini_flags=["ai_generation_artifacts"])
    assert service.score(analysis) == 0.75


def test_edited_flag_imposes_review_floor():
    analysis = ArtifactAnalysis(exif_score=0.0, ela_score=0.0,
        ai_flags=["cloned_region"], gemini_flags=["cloned_region"])
    assert service.score(analysis) == 0.4
