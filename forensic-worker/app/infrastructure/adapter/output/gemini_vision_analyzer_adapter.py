"""Adaptador de salida: GeminiVisionAnalyzerAdapter (T2.M6, ImageCognitiveAnalyzerPort).

Análisis visual de la imagen con Gemini (GEMINI_API_KEY): detecta señales de
manipulación/generación y las devuelve como gemini_flags.
"""
import base64
import json

import httpx

from app.domain.ports.image_cognitive_analyzer_port import ImageCognitiveAnalyzerPort

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
# gemini-2.0-flash fue retirado el 1 de junio de 2026.
_MODEL = "gemini-3.5-flash"
_TIMEOUT_SECONDS = 90.0

_PROMPT = """Eres un analista forense de imágenes. Clasifica únicamente señales visibles, sin asumir que una imagen es auténtica solo porque se ve realista. Busca:
- generación completa por IA: ai_generation_artifacts, synthetic_texture, anatomical_inconsistency;
- modificación localizada por IA: ai_inpainting_artifacts, generative_fill_artifacts;
- edición convencional: cloned_region, compositing_artifacts, inconsistent_lighting, warped_text;
- captura de pantalla: screenshot_ui_elements, screen_capture_artifacts.
Usa exclusivamente esas banderas. Una captura puede tener además señales de edición o IA.
Responde SOLO un JSON con esta forma: {"flags": ["..."]}. Devuelve una lista vacía únicamente cuando no exista evidencia visual suficiente."""

_IMAGE_MAGICS = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG", "image/png"),
    (b"RIFF", "image/webp"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
)


def _image_mime(content: bytes) -> str:
    for magic, mime in _IMAGE_MAGICS:
        if content.startswith(magic):
            return mime
    return "image/jpeg"  # default razonable: los IMAGE del pipeline vienen de content-type image/*


class GeminiVisionAnalyzerAdapter(ImageCognitiveAnalyzerPort):
    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient | None = None,
        base_url: str = _GEMINI_BASE_URL,
        model: str = _MODEL,
    ) -> None:
        self._api_key = api_key
        self._client = client
        self._base_url = base_url
        self._model = model

    async def analyze(self, image_bytes: bytes) -> list:
        url = f"{self._base_url}/models/{self._model}:generateContent"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": _image_mime(image_bytes),
                                "data": base64.b64encode(image_bytes).decode("ascii"),
                            }
                        },
                        {"text": _PROMPT},
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "OBJECT",
                    "properties": {
                        "flags": {
                            "type": "ARRAY",
                            "items": {
                                "type": "STRING",
                                "enum": [
                                    "ai_generation_artifacts", "synthetic_texture",
                                    "anatomical_inconsistency", "ai_inpainting_artifacts",
                                    "generative_fill_artifacts", "cloned_region",
                                    "compositing_artifacts", "inconsistent_lighting",
                                    "warped_text", "screenshot_ui_elements",
                                    "screen_capture_artifacts"
                                ]
                            }
                        }
                    },
                    "required": ["flags"]
                },
                "temperature": 0.0,
                "seed": 42
            },
        }
        headers = {"x-goog-api-key": self._api_key}

        client = self._client or httpx.AsyncClient(timeout=_TIMEOUT_SECONDS)
        owns_client = self._client is None
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        finally:
            if owns_client:
                await client.aclose()

        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
        return [str(flag) for flag in parsed.get("flags", [])]
