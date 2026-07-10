"""Adaptador de salida: DeepSeekAnalyzerAdapter (T2.M5, TextCognitiveAnalyzerPort).

Clasificación semántica del texto extraído por OCR usando la API de DeepSeek
(DEEPSEEK_API_KEY): tipo de documento, montos financieros y banderas de
sospecha. El vocabulario de document_type está alineado con
BenfordApplicabilityService.FINANCIAL_DOCUMENT_TYPES (T2.M7).
"""
import json

import httpx

from app.domain.ports.text_cognitive_analyzer_port import (
    TextCognitiveAnalyzerPort,
    TextCognitiveResult,
)

_DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
_MODEL = "deepseek-chat"
_TIMEOUT_SECONDS = 90.0
_MAX_TEXT_CHARS = 12_000  # acota tokens; suficiente para documentos típicos

_SYSTEM_PROMPT = """Eres un analista forense de documentos. Analiza el texto y responde SOLO un JSON con esta forma exacta:
{
  "document_type": "<uno de: invoice, receipt, bank_statement, financial_report, budget, payroll, tax_document, purchase_order, contract, id_document, letter, academic, news, other>",
  "financial_amounts": [<todos los montos monetarios que aparecen, como números sin símbolo ni separador de miles>],
  "ai_flags": [<banderas de sospecha en snake_case, ej: "inconsistent_totals", "generic_template_text", "possible_ai_generated_text", "missing_tax_id", "date_inconsistency". Lista vacía si no hay>]
}"""


class DeepSeekAnalyzerAdapter(TextCognitiveAnalyzerPort):
    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient | None = None,
        base_url: str = _DEEPSEEK_URL,
    ) -> None:
        self._api_key = api_key
        self._client = client
        self._base_url = base_url

    async def analyze(self, text: str) -> TextCognitiveResult:
        payload = {
            "model": _MODEL,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text[:_MAX_TEXT_CHARS]},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}

        client = self._client or httpx.AsyncClient(timeout=_TIMEOUT_SECONDS)
        owns_client = self._client is None
        try:
            response = await client.post(self._base_url, json=payload, headers=headers)
            response.raise_for_status()
        finally:
            if owns_client:
                await client.aclose()

        content = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        amounts = [
            float(a) for a in parsed.get("financial_amounts", []) if isinstance(a, (int, float))
        ]
        flags = [str(f) for f in parsed.get("ai_flags", [])]
        document_type = parsed.get("document_type")

        return TextCognitiveResult(
            document_type=str(document_type) if document_type else None,
            financial_amounts=amounts,
            ai_flags=flags,
        )
