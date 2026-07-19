"""GeminiVisionAnalyzerAdapter: salida estructurada y corroboración crítica."""
import json

import httpx

from app.infrastructure.adapter.output.gemini_vision_analyzer_adapter import GeminiVisionAnalyzerAdapter

JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def _finding(flag: str, confidence: str = "HIGH", evidence: str = "zona central") -> dict:
    return {"flag": flag, "confidence": confidence, "evidence": evidence}


def _client_returning(responses: list[list[dict]], captured: list) -> httpx.AsyncClient:
    pending = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        findings = pending.pop(0)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [
            {"text": json.dumps({"findings": findings})}
        ]}}]})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_returns_only_high_confidence_findings():
    captured = []
    adapter = GeminiVisionAnalyzerAdapter(api_key="gm-key", client=_client_returning([[
        _finding("cloned_region"), _finding("warped_text", "LOW")
    ]], captured))

    flags = await adapter.analyze(JPEG_BYTES)

    assert flags == ["cloned_region"]
    assert len(captured) == 1
    assert captured[0].headers["x-goog-api-key"] == "gm-key"
    assert "gemini-3.5-flash:generateContent" in str(captured[0].url)
    body = json.loads(captured[0].content)
    assert body["contents"][0]["parts"][0]["inline_data"]["mime_type"] == "image/jpeg"


async def test_critical_ai_flag_requires_second_confirmation():
    captured = []
    adapter = GeminiVisionAnalyzerAdapter(api_key="k", client=_client_returning([
        [_finding("ai_generation_artifacts")],
        [],
    ], captured))

    assert await adapter.analyze(JPEG_BYTES) == []
    assert len(captured) == 2


async def test_confirmed_critical_flag_is_kept():
    adapter = GeminiVisionAnalyzerAdapter(api_key="k", client=_client_returning([
        [_finding("ai_generation_artifacts")],
        [_finding("ai_generation_artifacts", evidence="manos incompatibles")],
    ], []))
    assert await adapter.analyze(JPEG_BYTES) == ["ai_generation_artifacts"]


async def test_empty_findings_return_empty_flags():
    adapter = GeminiVisionAnalyzerAdapter(api_key="k", client=_client_returning([[]], []))
    assert await adapter.analyze(JPEG_BYTES) == []
