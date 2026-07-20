import fitz
import pytest
from fastapi import HTTPException

from app.infrastructure.adapter.input.rest.analysis_controller import _resolve_and_validate_artifact


def _pdf_bytes() -> bytes:
    pdf = fitz.open()
    pdf.new_page().insert_text((72, 72), "Documento válido")
    content = pdf.tobytes()
    pdf.close()
    return content


def test_valid_pdf_is_text_artifact():
    assert _resolve_and_validate_artifact(_pdf_bytes()) == "TEXT"


@pytest.mark.parametrize("content", [b"PK\x03\x04docx", b"excel binario", b"", b"%PDF roto"])
def test_unsupported_or_damaged_document_is_rejected(content):
    with pytest.raises(HTTPException) as error:
        _resolve_and_validate_artifact(content)
    assert error.value.status_code == 400


def test_supported_image_is_detected_from_bytes_not_mime():
    assert _resolve_and_validate_artifact(b"\xff\xd8\xff" + b"x" * 20) == "IMAGE"


def test_upload_larger_than_limit_is_rejected():
    with pytest.raises(HTTPException) as error:
        _resolve_and_validate_artifact(b"x" * (50 * 1024 * 1024 + 1))
    assert error.value.status_code == 413
