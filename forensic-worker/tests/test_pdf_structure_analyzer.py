import fitz

from app.infrastructure.adapter.output.pymupdf_structure_analyzer_adapter import (
    PyMuPdfStructureAnalyzerAdapter,
)


def _pdf(metadata=None, attachment=False, active=False) -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Documento estructural de prueba")
    if metadata:
        pdf.set_metadata(metadata)
    if attachment:
        pdf.embfile_add("evidencia.txt", b"contenido", filename="evidencia.txt")
    if active:
        catalog = pdf.pdf_catalog()
        pdf.xref_set_key(catalog, "OpenAction", "<</S/JavaScript/JS(app.alert('x'))>>")
    content = pdf.tobytes()
    pdf.close()
    return content


async def test_clean_pdf_reports_neutral_structure():
    result = await PyMuPdfStructureAnalyzerAdapter().analyze(_pdf())

    assert result.score == 0.0
    assert result.flags == []
    assert result.evidence["incremental_updates"] == 0
    assert result.evidence["digital_signatures"] == []


async def test_metadata_date_contradiction_is_a_structural_signal():
    result = await PyMuPdfStructureAnalyzerAdapter().analyze(_pdf({
        "creator": "Adobe Acrobat",
        "creationDate": "D:20260718120000",
        "modDate": "D:20250718120000",
    }))

    assert result.score == 0.35
    assert "pdf_metadata_date_inconsistency" in result.flags
    assert "acrobat" in result.evidence["editing_software_detected"]


async def test_attachment_is_reported_without_automatic_fraud_penalty():
    result = await PyMuPdfStructureAnalyzerAdapter().analyze(_pdf(attachment=True))

    assert result.evidence["embedded_files"] == ["evidencia.txt"]
    assert result.score == 0.0


async def test_javascript_open_action_is_high_risk_active_content():
    result = await PyMuPdfStructureAnalyzerAdapter().analyze(_pdf(active=True))

    assert result.score == 0.7
    assert "pdf_suspicious_active_content" in result.flags
    assert "JAVASCRIPT" in result.evidence["active_content"]
    assert "OPEN_ACTION" in result.evidence["active_content"]
