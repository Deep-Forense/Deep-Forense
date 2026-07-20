"""Extracción híbrida de texto para PDF, imágenes y texto plano."""
import base64
import logging

import fitz
import httpx
from app.infrastructure.adapter.output.http_retry import post_with_retry

from app.domain.ports.ocr_port import EmbeddedImage, OcrExtraction, OcrPort

_DEEPINFRA_OPENAI_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
_MODEL = "deepseek-ai/DeepSeek-OCR"
_PROMPT = "Extract all the text from this document image. Return only the extracted text, no commentary."
_TIMEOUT_SECONDS = 120.0
_MAX_PDF_PAGES = 10
_PDF_TEXT_LAYER_MIN_CHARS = 50
_RASTER_DPI = 150
_MAX_EMBEDDED_IMAGES = 10
_MAX_VISUAL_IMAGES = 5
_MIN_EMBEDDED_IMAGE_SIDE = 128

_PDF_MAGIC = b"%PDF"
_IMAGE_MAGICS = (
    (b"\xff\xd8\xff", "image/jpeg"), (b"\x89PNG", "image/png"),
    (b"RIFF", "image/webp"), (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
)
logger = logging.getLogger(__name__)


def _image_mime(content: bytes) -> str | None:
    for magic, mime in _IMAGE_MAGICS:
        if content.startswith(magic):
            return mime
    return None


class DeepSeekOcrAdapter(OcrPort):
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None,
                 base_url: str = _DEEPINFRA_OPENAI_URL, model: str = _MODEL,
                 max_pdf_pages: int = _MAX_PDF_PAGES,
                 max_embedded_images: int = _MAX_EMBEDDED_IMAGES) -> None:
        self._api_key = api_key
        self._client = client
        self._base_url = base_url
        self._model = model
        self._max_pdf_pages = max(1, max_pdf_pages)
        self._max_embedded_images = max(0, max_embedded_images)

    async def extract_text(self, content: bytes) -> str:
        return (await self.extract_with_metadata(content)).text

    async def extract_with_metadata(self, content: bytes) -> OcrExtraction:
        if content.startswith(_PDF_MAGIC):
            return await self._extract_from_pdf(content)
        mime = _image_mime(content)
        if mime is not None:
            return OcrExtraction(text=await self._ocr_image(content, mime), ocr_pages=1)
        try:
            return OcrExtraction(text=content.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise ValueError("Contenido TEXT no reconocido: no es PDF, imagen ni UTF-8.") from exc

    async def _extract_from_pdf(self, content: bytes) -> OcrExtraction:
        with fitz.open(stream=content, filetype="pdf") as pdf:
            pages = list(pdf.pages(0, min(len(pdf), self._max_pdf_pages)))
            parts: list[str] = []
            text_layer_pages = 0
            ocr_pages = 0
            embedded_images = 0
            seen_xrefs: set[int] = set()
            ocr_xrefs: set[int] = set()
            embedded_for_ocr: list[tuple[bytes, str]] = []
            visual_images: list[EmbeddedImage] = []
            warnings: list[str] = []

            for page_number, page in enumerate(pages, start=1):
                page_text = page.get_text().strip()
                images = page.get_images(full=True)
                embedded_images += len(images)
                for image in images:
                    xref, width, height = image[0], image[2], image[3]
                    if (xref in seen_xrefs or min(width, height) < _MIN_EMBEDDED_IMAGE_SIDE
                            or len(visual_images) >= _MAX_VISUAL_IMAGES):
                        continue
                    image_bytes = pdf.extract_image(xref).get("image", b"")
                    if _image_mime(image_bytes):
                        seen_xrefs.add(xref)
                        visual_images.append(EmbeddedImage(
                            content=image_bytes, page_number=page_number,
                            width=width, height=height,
                        ))
                if len(page_text) >= _PDF_TEXT_LAYER_MIN_CHARS:
                    text_layer_pages += 1
                    parts.append(f"[Página {page_number} - texto digital]\n{page_text}")
                    for image in images:
                        xref, width, height = image[0], image[2], image[3]
                        if (xref in ocr_xrefs or min(width, height) < _MIN_EMBEDDED_IMAGE_SIDE
                                or len(embedded_for_ocr) >= self._max_embedded_images):
                            continue
                        ocr_xrefs.add(xref)
                        image_bytes = pdf.extract_image(xref).get("image", b"")
                        mime = _image_mime(image_bytes)
                        if mime:
                            embedded_for_ocr.append((image_bytes, mime))
                else:
                    ocr_pages += 1
                    png = page.get_pixmap(dpi=_RASTER_DPI, alpha=False).tobytes("png")
                    try:
                        page_ocr = await self._ocr_image(png, "image/png")
                    except Exception as exc:
                        logger.warning("OCR no disponible para página %s: %s", page_number, exc)
                        page_ocr = "[OCR no disponible]"
                        warnings.append(f"ocr_page_{page_number}_unavailable")
                    parts.append(f"[Página {page_number} - OCR]\n{page_ocr}")

            total_pages = len(pdf)

        for index, (image_bytes, mime) in enumerate(embedded_for_ocr, start=1):
            try:
                image_ocr = await self._ocr_image(image_bytes, mime)
            except Exception as exc:
                logger.warning("OCR no disponible para imagen embebida %s: %s", index, exc)
                image_ocr = "[OCR no disponible]"
                warnings.append(f"ocr_embedded_image_{index}_unavailable")
            parts.append(f"[Imagen embebida {index} - OCR]\n{image_ocr}")

        return OcrExtraction(
            text="\n\n".join(parts).strip(), page_count=total_pages,
            analyzed_pages=len(pages), text_layer_pages=text_layer_pages,
            ocr_pages=ocr_pages, embedded_images=embedded_images,
            truncated=total_pages > len(pages),
            visual_images=tuple(visual_images),
            warnings=tuple(warnings),
        )

    async def _ocr_image(self, image_bytes: bytes, mime: str) -> str:
        data_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": _PROMPT},
            ]}],
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        client = self._client or httpx.AsyncClient(timeout=_TIMEOUT_SECONDS)
        owns_client = self._client is None
        try:
            response = await post_with_retry(client, self._base_url, json=payload, headers=headers)
            response.raise_for_status()
        finally:
            if owns_client:
                await client.aclose()
        return response.json()["choices"][0]["message"]["content"]
