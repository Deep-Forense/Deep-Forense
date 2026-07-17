from app.domain.services.image_classification_service import ImageClassificationService

service = ImageClassificationService()


def test_prioritizes_full_ai_generation():
    result, _ = service.classify(["ai_generation_artifacts", "screenshot_ui_elements"], 0.2, 0.1)
    assert result == "AI_GENERATED"


def test_detects_ai_modification():
    result, _ = service.classify(["generative_fill_artifacts"], 0.2, 0.1)
    assert result == "AI_MODIFIED"


def test_detects_screenshot():
    result, _ = service.classify(["screenshot_ui_elements"], 0.2, 0.1)
    assert result == "SCREENSHOT"


def test_does_not_claim_authenticity_when_technical_signals_are_elevated():
    result, _ = service.classify([], 0.45, 0.3)
    assert result == "INCONCLUSIVE"
