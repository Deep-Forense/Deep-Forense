"""Tests de T2.M5 — DeepSeekAnalyzerAdapter (HTTP mockeado, sin cuota real)."""
import json

import httpx

from app.infrastructure.adapter.output.deepseek_analyzer_adapter import DeepSeekAnalyzerAdapter


def _client_returning(payload: dict, captured: list) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(payload)}}]},
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_parses_financial_document_response():
    captured = []
    adapter = DeepSeekAnalyzerAdapter(
        api_key="ds-key",
        client=_client_returning(
            {
                "document_type": "invoice",
                "financial_amounts": [1234.56, 789, 45.1],
                "ai_flags": ["inconsistent_totals"],
            },
            captured,
        ),
    )

    result = await adapter.analyze("FACTURA ... TOTAL $1.234,56")

    assert result.document_type == "invoice"
    assert result.financial_amounts == [1234.56, 789.0, 45.1]
    assert result.ai_flags == ["inconsistent_totals"]
    assert captured[0].headers["authorization"] == "Bearer ds-key"
    body = json.loads(captured[0].content)
    assert body["response_format"] == {"type": "json_object"}


async def test_non_financial_document_with_empty_fields():
    adapter = DeepSeekAnalyzerAdapter(
        api_key="k",
        client=_client_returning(
            {"document_type": "letter", "financial_amounts": [], "ai_flags": []}, []
        ),
    )

    result = await adapter.analyze("Querida abuela, te escribo para...")

    assert result.document_type == "letter"
    assert result.financial_amounts == []
    assert result.ai_flags == []


async def test_ignores_non_numeric_amounts_in_response():
    adapter = DeepSeekAnalyzerAdapter(
        api_key="k",
        client=_client_returning(
            {"document_type": "receipt", "financial_amounts": [10, "N/A", 20.5], "ai_flags": []},
            [],
        ),
    )

    result = await adapter.analyze("recibo")

    assert result.financial_amounts == [10.0, 20.5]
