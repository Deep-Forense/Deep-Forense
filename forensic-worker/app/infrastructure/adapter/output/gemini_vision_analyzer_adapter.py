"""Análisis visual conservador con Gemini y verificación de flags críticas."""
import base64
import json
import logging

import httpx
from app.infrastructure.adapter.output.http_retry import post_with_retry

from app.domain.ports.image_cognitive_analyzer_port import ImageCognitiveAnalyzerPort

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_MODEL = "gemini-3-flash-preview"
_TIMEOUT_SECONDS = 90.0
logger = logging.getLogger(__name__)

_ALL_FLAGS = [
    "ai_generation_artifacts", "synthetic_texture", "anatomical_inconsistency",
    "ai_inpainting_artifacts", "generative_fill_artifacts", "cloned_region",
    "compositing_artifacts", "inconsistent_lighting", "warped_text",
    "screenshot_ui_elements", "screen_capture_artifacts",
]
_CRITICAL_AI_FLAGS = set(_ALL_FLAGS[:5])

_PROMPT = """Analiza la imagen de forma conservadora. No infieras generación o edición
solo por estilo, belleza, desenfoque, compresión, ausencia de EXIF o apariencia inusual.
Reporta exclusivamente indicios VISIBLES y localizables:
- ai_generation_artifacts: varios defectos generativos inequívocos;
- synthetic_texture: textura repetitiva o no física claramente visible;
- anatomical_inconsistency: anatomía imposible claramente visible;
- ai_inpainting_artifacts o generative_fill_artifacts: transición localizada demostrable;
- cloned_region: región duplicada identificable;
- compositing_artifacts: borde, escala o perspectiva incompatibles y localizables;
- inconsistent_lighting: contradicción clara de dirección de luz o sombras;
- warped_text: solo si existe texto legible geométricamente deformado;
- screenshot_ui_elements o screen_capture_artifacts: interfaz o patrón de pantalla visible.

Para cada hallazgo indica flag, confidence y evidencia breve con su ubicación. Usa HIGH
solo cuando la evidencia sea inequívoca. Si hay una explicación fotográfica normal o no
puedes localizar el indicio, omítelo. Una imagen real no debe recibir flags por precaución."""

_FINDINGS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "findings": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "flag": {"type": "STRING", "enum": _ALL_FLAGS},
                    "confidence": {"type": "STRING", "enum": ["LOW", "MEDIUM", "HIGH"]},
                    "evidence": {"type": "STRING"},
                },
                "required": ["flag", "confidence", "evidence"],
            },
        }
    },
    "required": ["findings"],
}

_IMAGE_MAGICS = (
    (b"\xff\xd8\xff", "image/jpeg"), (b"\x89PNG", "image/png"),
    (b"RIFF", "image/webp"), (b"II*\x00", "image/tiff"), (b"MM\x00*", "image/tiff"),
)


def _image_mime(content: bytes) -> str:
    for magic, mime in _IMAGE_MAGICS:
        if content.startswith(magic):
            return mime
    return "image/jpeg"


class GeminiVisionAnalyzerAdapter(ImageCognitiveAnalyzerPort):
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None,
                 base_url: str = _GEMINI_BASE_URL, model: str = _MODEL) -> None:
        self._api_key = api_key.strip() if api_key else ""
        if not self._api_key:
            raise ValueError("La API key de Gemini está vacía o no configurada.")
        self._client = client
        self._base_url = base_url
        self._model = model

    async def analyze(self, image_bytes: bytes) -> list:
        findings = await self._request_findings(image_bytes, _PROMPT)
        high = self._high_confidence_flags(findings)
        critical = high & _CRITICAL_AI_FLAGS


        if critical:
            candidates = ", ".join(sorted(critical))
            verification_prompt = f"""Verifica de forma independiente y escéptica estos posibles
hallazgos: {candidates}. Intenta refutarlos con explicaciones fotográficas normales. Conserva
solo los que tengan evidencia visual inequívoca y localizable. Devuelve findings con el mismo
esquema, sin agregar flags nuevos."""
            verified = self._high_confidence_flags(
                await self._request_findings(image_bytes, verification_prompt)
            )
            high -= critical - verified

        flags = sorted(high)
        logger.info("Gemini visual flags verificadas: %s", flags)
        return flags

    @staticmethod
    def _high_confidence_flags(findings: list[dict]) -> set[str]:
        return {
            str(item["flag"]) for item in findings
            if item.get("confidence") == "HIGH" and str(item.get("evidence", "")).strip()
        }

    async def _request_findings(self, image_bytes: bytes, prompt: str) -> list[dict]:
        url = f"{self._base_url}/models/{self._model}:generateContent"
        payload = {
            "contents": [{"parts": [
                {"inline_data": {"mime_type": _image_mime(image_bytes),
                                  "data": base64.b64encode(image_bytes).decode("ascii")}},
                {"text": prompt},
            ]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "response_schema": _FINDINGS_SCHEMA,
                "temperature": 0.0,
                "seed": 42,
            },
        }
        headers = {"x-goog-api-key": self._api_key}
        client = self._client or httpx.AsyncClient(timeout=_TIMEOUT_SECONDS)
        owns_client = self._client is None
        try:
            response = await post_with_retry(client, url, json=payload, headers=headers)
            response.raise_for_status()
        finally:
            if owns_client:
                await client.aclose()

        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
        return [item for item in parsed.get("findings", []) if isinstance(item, dict)]
