"""Análisis semántico documental conservador mediante API OpenAI-compatible."""
import json
import logging

import httpx

from app.domain.ports.text_cognitive_analyzer_port import TextCognitiveAnalyzerPort, TextCognitiveResult
from app.infrastructure.adapter.output.http_retry import post_with_retry

_DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
_MODEL = "deepseek-chat"
_TIMEOUT_SECONDS = 90.0
_MAX_TEXT_CHARS = 12_000
_AI_ORIGIN_FLAGS = {"possible_ai_generated_text", "possible_ai_edited_text"}

_SYSTEM_PROMPT = """Analiza conservadoramente el texto de un documento y responde SOLO JSON:
{
  "document_type": "invoice|receipt|bank_statement|financial_report|budget|payroll|tax_document|purchase_order|contract|id_document|letter|academic|news|other",
  "financial_amounts": [numeros monetarios],
  "ai_findings": [{"flag": "possible_ai_generated_text|possible_ai_edited_text|inconsistent_totals|generic_template_text|missing_tax_id|date_inconsistency", "confidence": "LOW|MEDIUM|HIGH", "evidence": "fragmento o contradiccion localizable"}]
}
Usa possible_ai_generated_text HIGH solo ante múltiples señales lingüísticas fuertes y localizables compatibles con generación integral. Usa possible_ai_edited_text HIGH solo ante transiciones, inserciones o reescrituras localizadas claramente incompatibles con el resto. No marques IA por redacción correcta, tono formal, listas, ausencia de errores, frases comunes o porque el usuario diga que fue generado con IA. Si no hay evidencia fuerte, omite esas flags."""
logger = logging.getLogger(__name__)


def _message_text(message: dict) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(
            str(part.get("text", "")) for part in content if isinstance(part, dict)
        ).strip()
    return ""


def _parse_json_object(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines and lines[-1].strip().startswith("```") else lines[1:])
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("El proveedor devolvió contenido vacío o sin un objeto JSON válido.")


class DeepSeekAnalyzerAdapter(TextCognitiveAnalyzerPort):
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None,
                 base_url: str = _DEEPSEEK_URL, model: str = _MODEL) -> None:
        self._api_key = api_key.strip() if api_key else ""
        if not self._api_key:
            raise ValueError("La API key de DeepSeek está vacía o no configurada.")
        self._client = client
        self._base_url = base_url
        self._model = model

    async def analyze(self, text: str) -> TextCognitiveResult:
        parsed = await self._request(text[:_MAX_TEXT_CHARS], _SYSTEM_PROMPT)
        findings = parsed.get("ai_findings", [])
        high_flags = {
            str(item.get("flag")) for item in findings if isinstance(item, dict)
            and item.get("confidence") == "HIGH" and str(item.get("evidence", "")).strip()
        }

        high_flags.update(str(flag) for flag in parsed.get("ai_flags", []) if flag)

        critical = high_flags & _AI_ORIGIN_FLAGS
        if critical:
            verification_prompt = f"""Evalúa de forma independiente y escéptica únicamente estas hipótesis: {', '.join(sorted(critical))}.
Intenta refutarlas con explicaciones humanas normales. Responde SOLO JSON con ai_findings; conserva una flag en HIGH únicamente si hay evidencia textual fuerte, específica y localizable. No agregues flags nuevas."""
            verified_payload = await self._request(text[:_MAX_TEXT_CHARS], verification_prompt)
            verified = {
                str(item.get("flag")) for item in verified_payload.get("ai_findings", [])
                if isinstance(item, dict) and item.get("confidence") == "HIGH"
                and str(item.get("evidence", "")).strip()
            }
            high_flags -= critical - verified

        amounts = [
            float(amount) for amount in parsed.get("financial_amounts", [])
            if isinstance(amount, (int, float))
        ]
        document_type = parsed.get("document_type")
        return TextCognitiveResult(
            document_type=str(document_type) if document_type else None,
            financial_amounts=amounts,
            ai_flags=sorted(high_flags),
        )

    async def _request(self, text: str, system_prompt: str) -> dict:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        client = self._client or httpx.AsyncClient(timeout=_TIMEOUT_SECONDS)
        owns_client = self._client is None
        try:
            response = await post_with_retry(client, self._base_url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
            choice = body.get("choices", [{}])[0]
            raw = _message_text(choice.get("message", {}))
            if not raw:
                logger.warning("Respuesta semántica vacía; finish_reason=%s model=%s", choice.get("finish_reason"), self._model)
            return _parse_json_object(raw)
        finally:
            if owns_client:
                await client.aclose()
