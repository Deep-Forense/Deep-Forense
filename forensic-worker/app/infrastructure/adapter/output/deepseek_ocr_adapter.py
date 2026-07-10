"""Adaptador de salida: DeepSeekOcrAdapter (T2.M4, OcrPort).

Extrae texto de artifacts TEXT usando DeepSeek-OCR vía DeepInfra
(API OpenAI-compatible, key = DEEPSEEK_OCR_DEEPINFRA_API_KEY).

Estrategia por tipo de contenido (detección por magic bytes):
  - PDF con capa de texto -> PyMuPDF (gratis, sin llamar la API).
  - PDF escaneado (sin texto) -> rasteriza páginas (PyMuPDF) y OCR por página.
  - Imagen (JPEG/PNG/WebP/TIFF) -> OCR directo.
  - Texto plano UTF-8 -> se devuelve decodificado.

El httpx.AsyncClient se inyecta por constructor para testear con
httpx.MockTransport sin gastar cuota real (regla de testing del Sprint 2).
"""
import base64

import fitz  # PyMuPDF
import httpx

from app.domain.ports.ocr_port import OcrPort

_DEEPINFRA_OPENAI_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
_MODEL = "deepseek-ai/DeepSeek-OCR"
_PROMPT = "Extract all the text from this document image. Return only the extracted text, no commentary."
_TIMEOUT_SECONDS = 120.0
_MAX_PDF_PAGES = 10  # acota costo/latencia en PDFs largos
_PDF_TEXT_LAYER_MIN_CHARS = 50  # menos que esto => tratamos el PDF como escaneado
_RASTER_DPI = 150

_PDF_MAGIC = b"%PDF"
_IMAGE_MAGICS = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG", "image/png"),
    (b"RIFF", "image/webp"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
)


def _image_mime(content: bytes) -> str | None:
    for magic, mime in _IMAGE_MAGICS:
        if content.startswith(magic):
            return mime
    return None


class DeepSeekOcrAdapter(OcrPort):
    def __init__(
        self,
        api_key: str,
        client: httpx.AsyncClient | None = None,
        base_url: str = _DEEPINFRA_OPENAI_URL,
    ) -> None:
        self._api_key = api_key
        self._client = client
        self._base_url = base_url

    async def extract_text(self, content: bytes) -> str:
        if content.startswith(_PDF_MAGIC):
            return await self._extract_from_pdf(content)

        mime = _image_mime(content)
        if mime is not None:
            return await self._ocr_image(content, mime)

        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Contenido TEXT no reconocido: no es PDF, imagen ni UTF-8.") from exc

    async def _extract_from_pdf(self, content: bytes) -> str:
        with fitz.open(stream=content, filetype="pdf") as pdf:
            pages = list(pdf.pages(0, min(len(pdf), _MAX_PDF_PAGES)))

            text_layer = "\n".join(page.get_text() for page in pages).strip()
            if len(text_layer) >= _PDF_TEXT_LAYER_MIN_CHARS:
                return text_layer

            # PDF escaneado: rasterizar y OCR página por página.
            page_pngs = [page.get_pixmap(dpi=_RASTER_DPI).tobytes("png") for page in pages]

        page_texts = [await self._ocr_image(png, "image/png") for png in page_pngs]
        return "\n".join(page_texts)

    async def _ocr_image(self, image_bytes: bytes, mime: str) -> str:
        data_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        payload = {
            "model": _MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {"type": "text", "text": _PROMPT},
                    ],
                }
            ],
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

        return response.json()["choices"][0]["message"]["content"]
