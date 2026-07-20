"""Comprobaciones aritméticas deterministas sobre texto financiero."""
import re
from dataclasses import dataclass

_AMOUNT = re.compile(r"[-+]?\d[\d.,]*")
_LINE_ITEM = re.compile(
    r"(?P<quantity>\d+(?:[.,]\d+)?)\s*[x×*]\s*"
    r"(?P<unit>\d[\d.,]*)\s*(?:=|:)\s*(?P<total>\d[\d.,]*)",
    re.IGNORECASE,
)
_LABELS = {
    "subtotal": ("subtotal", "base imponible"),
    "tax": ("iva", "impuesto", "tax"),
    "total": ("total a pagar", "importe total", "grand total", "total"),
}


_PARENTHETICAL = re.compile(r"\([^)]*\)")
_PERCENT_FIGURE = re.compile(r"\d[\d.,]*\s*%")


@dataclass(frozen=True)
class DocumentConsistencyResult:
    score: float | None
    checks: list[dict]
    flags: list[str]


def _number(raw: str) -> float | None:
    value = raw.strip()
    if not value:
        return None
    if "," in value and "." in value:
        decimal = "," if value.rfind(",") > value.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        value = value.replace(thousands, "").replace(decimal, ".")
    elif "," in value:
        tail = value.rsplit(",", 1)[1]
        value = value.replace(",", "." if len(tail) in (1, 2) else "")
    elif value.count(".") > 1:
        value = value.replace(".", "")
    try:
        return float(value)
    except ValueError:
        return None


def _amount_in_line(line: str) -> float | None:
    cleaned = _PERCENT_FIGURE.sub(" ", _PARENTHETICAL.sub(" ", line))
    matches = _AMOUNT.findall(cleaned)
    return _number(matches[-1]) if matches else None


def _labeled_amounts(text: str) -> dict[str, float]:
    found: dict[str, float] = {}
    lines = text.splitlines()
    for index, line in enumerate(lines):
        lowered = line.lower()
        for key, labels in _LABELS.items():
            if key in found or not any(label in lowered for label in labels):
                continue
            if key == "total" and ("subtotal" in lowered or "base imponible" in lowered):
                continue
            amount = _amount_in_line(line)
            if amount is None and index + 1 < len(lines):

                amount = _amount_in_line(lines[index + 1])
            if amount is not None:
                found[key] = amount
    return found


def _risk(difference: float, reference: float) -> float:
    relative = difference / max(abs(reference), 1.0)
    return round(min(1.0, max(0.4, relative * 10)), 4)


class DocumentConsistencyService:
    def analyze(self, text: str) -> DocumentConsistencyResult:
        values = _labeled_amounts(text)
        checks: list[dict] = []
        flags: list[str] = []
        risks: list[float] = []

        if all(key in values for key in ("subtotal", "tax", "total")):
            expected = values["subtotal"] + values["tax"]
            difference = abs(values["total"] - expected)
            passed = difference <= max(0.02, abs(values["total"]) * 0.001)
            checks.append({
                "rule": "subtotal_plus_tax_equals_total", "passed": passed,
                "subtotal": values["subtotal"], "tax": values["tax"],
                "reported_total": values["total"], "expected_total": round(expected, 2),
                "difference": round(difference, 2),
            })
            if not passed:
                flags.append("arithmetic_total_mismatch")
                risks.append(_risk(difference, values["total"]))

        line_totals: list[float] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            match = _LINE_ITEM.search(line)
            if not match:
                continue
            quantity = _number(match.group("quantity"))
            unit = _number(match.group("unit"))
            reported = _number(match.group("total"))
            if None in (quantity, unit, reported):
                continue
            expected = quantity * unit
            difference = abs(reported - expected)
            passed = difference <= max(0.02, abs(reported) * 0.001)
            line_totals.append(reported)
            checks.append({
                "rule": "quantity_times_unit_price", "line": line_number,
                "passed": passed, "quantity": quantity, "unit_price": unit,
                "reported_total": reported, "expected_total": round(expected, 2),
                "difference": round(difference, 2),
            })
            if not passed:
                flags.append("line_item_total_mismatch")
                risks.append(_risk(difference, reported))

        if line_totals and "subtotal" in values:
            expected_subtotal = sum(line_totals)
            difference = abs(values["subtotal"] - expected_subtotal)
            passed = difference <= max(0.02, abs(values["subtotal"]) * 0.001)
            checks.append({
                "rule": "line_items_sum_equals_subtotal", "passed": passed,
                "line_items": len(line_totals), "reported_subtotal": values["subtotal"],
                "expected_subtotal": round(expected_subtotal, 2),
                "difference": round(difference, 2),
            })
            if not passed:
                flags.append("line_items_subtotal_mismatch")
                risks.append(_risk(difference, values["subtotal"]))

        if not checks:
            return DocumentConsistencyResult(None, [], [])
        return DocumentConsistencyResult(
            score=max(risks, default=0.0), checks=checks,
            flags=list(dict.fromkeys(flags)),
        )
