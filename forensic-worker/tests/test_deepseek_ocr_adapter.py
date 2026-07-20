"""Tests de T2.M4 — DeepSeekOcrAdapter.

La llamada HTTP a DeepInfra se mockea con httpx.MockTransport: ningún test
gasta cuota real de la API (regla de testing del Sprint 2).
"""
import io
import json

import fitz
import httpx
from PIL import Image

from app.infrastructure.adapter.output.deepseek_ocr_adapter import DeepSeekOcrAdapter


def _mock_client(response_text: str, captured: list) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": response_text}}]},
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), color=(255, 255, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _pdf_with_text_layer(text: str) -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), text)
    return pdf.tobytes()


def _mixed_pdf(text: str) -> bytes:
    pdf = fitz.open()
    pdf.new_page().insert_text((72, 72), text)
    pdf.new_page()
    return pdf.tobytes()


def _pdf_with_embedded_image(text: str) -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), text)
    image = Image.new("RGB", (200, 160), color=(230, 230, 230))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    page.insert_image(fitz.Rect(72, 100, 272, 260), stream=buffer.getvalue())
    return pdf.tobytes()


async def test_image_goes_through_ocr_api(monkeypatch):
    captured = []
    adapter = DeepSeekOcrAdapter(api_key="test-key", client=_mock_client("TEXTO EXTRAIDO", captured))

    result = await adapter.extract_text(_png_bytes())

    assert result == "TEXTO EXTRAIDO"
    assert len(captured) == 1
    assert captured[0].headers["authorization"] == "Bearer test-key"
    body = json.loads(captured[0].content)
    assert body["model"] == "deepseek-ai/DeepSeek-OCR"
    assert body["messages"][0]["content"][0]["image_url"]["url"].startswith("data:image/png;base64,")


async def test_pdf_with_text_layer_skips_ocr_api():
    captured = []
    text = "Factura No 001-2026. Total: $1,234.56. " * 5
    adapter = DeepSeekOcrAdapter(api_key="k", client=_mock_client("NO DEBERIA LLAMARSE", captured))

    result = await adapter.extract_text(_pdf_with_text_layer(text))

    assert "Factura No 001-2026" in result
    assert captured == []


async def test_plain_utf8_text_is_returned_directly():
    captured = []
    adapter = DeepSeekOcrAdapter(api_key="k", client=_mock_client("NO", captured))

    result = await adapter.extract_text("hola mundo financiero".encode("utf-8"))

    assert result == "hola mundo financiero"
    assert captured == []


async def test_mixed_pdf_uses_text_layer_and_ocr_per_page():
    captured = []
    text = "Factura digital con contenido suficiente. " * 4
    adapter = DeepSeekOcrAdapter(api_key="k", client=_mock_client("PÁGINA ESCANEADA", captured))

    extraction = await adapter.extract_with_metadata(_mixed_pdf(text))

    assert "Factura digital" in extraction.text
    assert "PÁGINA ESCANEADA" in extraction.text
    assert extraction.page_count == 2
    assert extraction.analyzed_pages == 2
    assert extraction.text_layer_pages == 1
    assert extraction.ocr_pages == 1
    assert len(captured) == 1


async def test_embedded_image_is_exposed_as_original_visual_evidence():
    captured = []
    text = "Documento digital con una imagen embebida relevante. " * 4
    adapter = DeepSeekOcrAdapter(api_key="k", client=_mock_client("TEXTO DE IMAGEN", captured))

    extraction = await adapter.extract_with_metadata(_pdf_with_embedded_image(text))

    assert extraction.embedded_images == 1
    assert len(extraction.visual_images) == 1
    assert extraction.visual_images[0].content.startswith(b"\x89PNG")
    assert extraction.visual_images[0].page_number == 1
    assert "TEXTO DE IMAGEN" in extraction.text
