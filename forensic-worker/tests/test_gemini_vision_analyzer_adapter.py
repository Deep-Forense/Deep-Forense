"""Tests de T2.M6 — GeminiVisionAnalyzerAdapter (HTTP mockeado, sin cuota real)."""
import json

import httpx

from app.infrastructure.adapter.output.gemini_vision_analyzer_adapter import (
    GeminiVisionAnalyzerAdapter,
)

JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def _client_returning(flags: list, captured: list) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": json.dumps({"flags": flags})}]}}
                ]
            },
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_returns_flags_from_gemini():
    captured = []
    adapter = GeminiVisionAnalyzerAdapter(
        api_key="gm-key", client=_client_returning(["cloned_region", "warped_text"], captured)
    )

    flags = await adapter.analyze(JPEG_BYTES)

    assert flags == ["cloned_region", "warped_text"]
    request = captured[0]
    assert request.headers["x-goog-api-key"] == "gm-key"
    assert "gemini-2.0-flash:generateContent" in str(request.url)
    body = json.loads(request.content)
    assert body["contents"][0]["parts"][0]["inline_data"]["mime_type"] == "image/jpeg"


async def test_authentic_image_returns_empty_flags():
    adapter = GeminiVisionAnalyzerAdapter(api_key="k", client=_client_returning([], []))
    assert await adapter.analyze(JPEG_BYTES) == []
