"""Tests de T2.M7 — BenfordApplicabilityService (dominio puro, sin mocks).

Criterio de aceptación explícito del backlog: un texto NO financiero nunca
produce benford_score => applies_to_text debe ser False sin importar cuántos
montos tenga.
"""
from app.domain.services.benford_applicability_service import BenfordApplicabilityService

JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 16
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16

MANY_AMOUNTS = [float(i) for i in range(1, 31)]  # 30 montos


def test_non_financial_text_never_applies_even_with_many_amounts():
    service = BenfordApplicabilityService(min_amount_count=15)
    assert service.applies_to_text("letter", MANY_AMOUNTS) is False
    assert service.applies_to_text("academic", MANY_AMOUNTS) is False
    assert service.applies_to_text("other", MANY_AMOUNTS) is False
    assert service.applies_to_text(None, MANY_AMOUNTS) is False


def test_financial_text_with_enough_amounts_applies():
    service = BenfordApplicabilityService(min_amount_count=15)
    assert service.applies_to_text("invoice", MANY_AMOUNTS) is True
    assert service.applies_to_text("bank_statement", MANY_AMOUNTS) is True


def test_financial_text_with_few_amounts_does_not_apply():
    service = BenfordApplicabilityService(min_amount_count=15)
    assert service.applies_to_text("invoice", [10.0, 20.0, 30.0]) is False
    assert service.applies_to_text("invoice", []) is False
    assert service.applies_to_text("invoice", None) is False


def test_threshold_is_configurable_via_min_amount_count():
    service = BenfordApplicabilityService(min_amount_count=3)
    assert service.applies_to_text("receipt", [1.0, 2.0, 3.0]) is True
    assert service.applies_to_text("receipt", [1.0, 2.0]) is False


def test_document_type_matching_is_case_insensitive():
    service = BenfordApplicabilityService(min_amount_count=1)
    assert service.applies_to_text("Invoice", [1.0]) is True
    assert service.applies_to_text("INVOICE", [1.0]) is True


def test_image_applicability_is_jpeg_only():
    service = BenfordApplicabilityService()
    assert service.applies_to_image(JPEG_BYTES) is True
    assert service.applies_to_image(PNG_BYTES) is False
    assert service.applies_to_image(b"") is False
