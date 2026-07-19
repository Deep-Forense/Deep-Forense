"""Inspección estructural PDF y validación local de firmas con pyHanko."""
import asyncio
import io
import re

import fitz
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature

from app.domain.ports.pdf_structure_analyzer_port import (
    PdfStructureAnalyzerPort,
    PdfStructureResult,
)

_EDITING_SOFTWARE = ("photoshop", "illustrator", "acrobat", "libreoffice", "word", "canva")
_ACTIVE_MARKERS = {
    b"/JavaScript": "JAVASCRIPT",
    b"/JS": "JAVASCRIPT",
    b"/OpenAction": "OPEN_ACTION",
    b"/Launch": "LAUNCH_ACTION",
    b"/SubmitForm": "SUBMIT_FORM",
}


def _pdf_date_key(value: str) -> str | None:
    digits = "".join(re.findall(r"\d", value or ""))
    return digits[:14].ljust(14, "0") if len(digits) >= 4 else None


def _signature_evidence(content: bytes) -> list[dict]:
    signatures: list[dict] = []
    try:
        reader = PdfFileReader(io.BytesIO(content))
        for embedded in reader.embedded_signatures:
            item = {"field_name": embedded.field_name, "validation_status": "ERROR"}
            try:
                status = validate_pdf_signature(embedded)
                modification = getattr(status, "modification_level", None)
                signer = getattr(status, "signing_cert", None) or getattr(status, "signer_cert", None)
                item.update({
                    "validation_status": "VALID" if bool(status.valid) and bool(status.intact) else "INVALID",
                    "cryptographically_valid": bool(status.valid),
                    "intact": bool(status.intact),
                    "trusted": bool(getattr(status, "trusted", False)),
                    "docmdp_ok": bool(getattr(status, "docmdp_ok", True)),
                    "modification_level": getattr(modification, "name", str(modification)) if modification else None,
                    "signer_subject": getattr(getattr(signer, "subject", None), "human_friendly", None),
                })
            except Exception as exc:
                item["error"] = type(exc).__name__
            signatures.append(item)
    except Exception:
        return []
    return signatures


class PyMuPdfStructureAnalyzerAdapter(PdfStructureAnalyzerPort):
    async def analyze(self, content: bytes) -> PdfStructureResult:
        return await asyncio.to_thread(self._analyze_sync, content)

    @staticmethod
    def _analyze_sync(content: bytes) -> PdfStructureResult:
        with fitz.open(stream=content, filetype="pdf") as pdf:
            metadata = {key: value for key, value in (pdf.metadata or {}).items() if value}
            annotations = 0
            form_fields = 0
            signature_fields = 0
            unique_fonts: set[str] = set()
            overlapping_objects = 0
            for page in pdf:
                annotations += sum(1 for _ in (page.annots() or ()))
                widgets = list(page.widgets() or ())
                form_fields += len(widgets)
                signature_fields += sum(
                    1 for widget in widgets if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE
                )
                unique_fonts.update(font[3] for font in page.get_fonts(full=True) if len(font) > 3)
                blocks = page.get_text("dict").get("blocks", [])
                text_rects = [fitz.Rect(block["bbox"]) for block in blocks if block.get("type") == 0]
                image_rects = [fitz.Rect(block["bbox"]) for block in blocks if block.get("type") == 1]
                overlapping_objects += sum(
                    1 for text in text_rects for image in image_rects
                    if not (text & image).is_empty and (text & image).get_area() > 4
                )

            try:
                layers = len(pdf.get_ocgs())
            except Exception:
                layers = 0
            embedded_files = list(pdf.embfile_names())
            repaired = bool(pdf.is_repaired)
            sig_flags = pdf.get_sigflags()
            structural_objects = "\n".join(
                pdf.xref_object(xref, compressed=False) for xref in range(1, pdf.xref_length())
            ).encode("latin-1", errors="ignore")

        revisions = max(content.count(b"%%EOF"), content.count(b"startxref"))
        incremental_updates = max(0, revisions - 1)
        active_content = sorted({
            label for marker, label in _ACTIVE_MARKERS.items() if marker in structural_objects
        })
        signatures = _signature_evidence(content)
        creation = _pdf_date_key(metadata.get("creationDate", ""))
        modification = _pdf_date_key(metadata.get("modDate", ""))
        date_inconsistent = bool(creation and modification and modification < creation)
        producer = " ".join((metadata.get("creator", ""), metadata.get("producer", ""))).lower()
        editing_software = [name for name in _EDITING_SOFTWARE if name in producer]

        flags: list[str] = []
        scores: list[float] = []
        if repaired:
            flags.append("pdf_repaired_structure")
            scores.append(0.4)
        if active_content:
            flags.append("pdf_suspicious_active_content")
            scores.append(0.7)
        if date_inconsistent:
            flags.append("pdf_metadata_date_inconsistency")
            scores.append(0.35)
        if any(signature.get("validation_status") == "INVALID" for signature in signatures):
            flags.append("pdf_invalid_digital_signature")
            scores.append(0.9)
        if any(signature.get("docmdp_ok") is False for signature in signatures):
            flags.append("pdf_modified_after_signature")
            scores.append(0.9)

        evidence = {
            "metadata": metadata,
            "editing_software_detected": editing_software,
            "incremental_updates": incremental_updates,
            "repaired": repaired,
            "annotations": annotations,
            "form_fields": form_fields,
            "signature_fields": signature_fields,
            "signature_flags": sig_flags,
            "digital_signatures": signatures,
            "embedded_files": embedded_files,
            "optional_content_groups": layers,
            "unique_fonts": len(unique_fonts),
            "overlapping_text_image_objects": overlapping_objects,
            "active_content": active_content,
        }
        return PdfStructureResult(score=max(scores, default=0.0), flags=flags, evidence=evidence)
