"""Clasificación explicable de una imagen a partir de señales forenses presentes."""

AI_GENERATED_FLAGS = {"ai_generation_artifacts", "synthetic_texture", "anatomical_inconsistency"}
AI_MODIFIED_FLAGS = {"ai_inpainting_artifacts", "generative_fill_artifacts"}
SCREENSHOT_FLAGS = {"screenshot_ui_elements", "screen_capture_artifacts"}
EDITED_FLAGS = {"cloned_region", "compositing_artifacts", "inconsistent_lighting", "warped_text"}

MESSAGES = {
    "AI_GENERATED": "Se detectaron señales visuales compatibles con una imagen generada por IA.",
    "AI_MODIFIED": "Se detectaron regiones compatibles con modificación mediante IA.",
    "SCREENSHOT": "La evidencia presenta características compatibles con una captura de pantalla.",
    "EDITED": "Se detectaron señales compatibles con edición o composición de la imagen.",
    "AUTHENTIC": "No se detectaron señales suficientes de generación o modificación; esto no prueba autenticidad.",
    "INCONCLUSIVE": "Las señales disponibles no permiten clasificar el origen de la imagen con suficiente claridad.",
}

CLASSIFICATION_RISK_FLOORS = {"AI_GENERATED": 0.75, "AI_MODIFIED": 0.75, "EDITED": 0.40}


def classification_from_flags(flags: list[str]) -> str | None:
    present = set(flags)
    if present & AI_GENERATED_FLAGS:
        return "AI_GENERATED"
    if present & AI_MODIFIED_FLAGS:
        return "AI_MODIFIED"
    if present & SCREENSHOT_FLAGS:
        return "SCREENSHOT"
    if present & EDITED_FLAGS:
        return "EDITED"
    return None


def risk_floor_for_flags(flags: list[str]) -> float:
    return CLASSIFICATION_RISK_FLOORS.get(classification_from_flags(flags), 0.0)


class ImageClassificationService:
    def classify(self, flags: list[str], exif_score: float, ela_score: float) -> tuple[str, str]:
        classification = classification_from_flags(flags)
        if classification is None and exif_score <= 0.2 and ela_score < 0.15:
            classification = "AUTHENTIC"
        elif classification is None:
            classification = "INCONCLUSIVE"
        return classification, MESSAGES[classification]
