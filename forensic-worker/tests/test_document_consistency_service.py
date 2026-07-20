from app.domain.services.document_consistency_service import DocumentConsistencyService


def test_matching_subtotal_tax_and_total_has_zero_risk():
    result = DocumentConsistencyService().analyze(
        "Subtotal: 100,00\nIVA: 12,00\nTotal a pagar: 112,00"
    )
    assert result.score == 0.0
    assert result.flags == []
    assert result.checks[0]["passed"] is True


def test_inconsistent_total_produces_deterministic_flag():
    result = DocumentConsistencyService().analyze(
        "Subtotal $1,000.00\nTax $120.00\nGrand total $1,500.00"
    )
    assert result.score >= 0.4
    assert result.flags == ["arithmetic_total_mismatch"]
    assert result.checks[0]["expected_total"] == 1120.0


def test_check_is_not_applicable_without_required_fields():
    result = DocumentConsistencyService().analyze("Total: 50.00")
    assert result.score is None
    assert result.checks == []


def test_line_items_and_subtotal_are_checked_deterministically():
    result = DocumentConsistencyService().analyze(
        "Producto A 2 x 10,00 = 20,00\nProducto B 3 x 5,00 = 15,00\nSubtotal: 35,00"
    )
    assert result.score == 0.0
    assert len(result.checks) == 3
    assert all(check["passed"] for check in result.checks)


def test_incorrect_line_total_is_flagged():
    result = DocumentConsistencyService().analyze(
        "Producto 3 x 10.00 = 50.00\nSubtotal: 50.00"
    )
    assert "line_item_total_mismatch" in result.flags
    assert result.score >= 0.4


def test_trailing_reference_after_total_is_not_taken_as_the_amount():

    result = DocumentConsistencyService().analyze(
        "Subtotal: 100,00\nIVA: 12,00\nTotal a pagar: 112,00 (Ref. 2024)"
    )
    assert result.checks[0]["reported_total"] == 112.0
    assert result.checks[0]["passed"] is True


def test_trailing_percentage_after_tax_is_not_taken_as_the_amount():

    result = DocumentConsistencyService().analyze(
        "Subtotal: 100,00\nIVA (21%): 21,00\nTotal a pagar: 121,00"
    )
    assert result.checks[0]["tax"] == 21.0
    assert result.checks[0]["passed"] is True


def test_table_layout_with_label_and_amount_on_separate_lines_is_detected():

    result = DocumentConsistencyService().analyze(
        "Subtotal:\nUSD 13,214.98\nIVA (12%):\nUSD 1,585.80\n"
        "Total a pagar:\nUSD 13,950.78\nCondiciones: pago mediante transferencia bancaria"
    )
    assert result.checks[0]["subtotal"] == 13214.98
    assert result.checks[0]["tax"] == 1585.80
    assert result.checks[0]["reported_total"] == 13950.78
    assert result.checks[0]["expected_total"] == 14800.78
    assert result.checks[0]["passed"] is False
    assert "arithmetic_total_mismatch" in result.flags
    assert result.score >= 0.4
