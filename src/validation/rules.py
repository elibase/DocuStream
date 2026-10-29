"""Deterministic invoice checks."""

from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
import re


REQUIRED_FIELDS = (
    "source_file", "invoice_number", "vendor_name", "invoice_date",
    "currency", "subtotal", "tax", "total",
)


def validate_required_fields_and_dates(record):
    """Return all check failures. due_date may be absent, null, or blank.

    Dates must be real calendar dates in exactly YYYY-MM-DD format.
    Presence does not imply that amounts or other field values are valid.
    """
    reasons = []
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            reasons.append(f"Missing required field: {field}")

    for field in ("invoice_date", "due_date"):
        value = record.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            reasons.append(f"Invalid date for {field}: expected YYYY-MM-DD")
            continue
        try:
            date.fromisoformat(value)
        except ValueError:
            reasons.append(f"Invalid calendar date for {field}: {value}")

    return reasons


def validate_amounts(record):
    """Require finite nonnegative amounts; allow a one-cent total difference."""
    reasons = []
    amounts = {}
    for field in ("subtotal", "tax", "total"):
        value = record.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue  # Already reported by the required-field checks.
        try:
            if isinstance(value, bool):
                raise ValueError
            amount = Decimal(str(value))
            if not amount.is_finite() or amount < 0:
                raise ValueError
            # Bound size and precision to keep arithmetic predictable.
            if amount > Decimal("999999999999.99") or amount != amount.quantize(Decimal("0.01")):
                raise ValueError
            amounts[field] = amount
        except (InvalidOperation, ValueError):
            reasons.append(f"Invalid amount for {field}: expected a non-negative decimal with at most two fractional digits, up to 999999999999.99")
    if len(amounts) == 3:
        with localcontext() as context:
            context.prec = 32
            if abs(amounts["subtotal"] + amounts["tax"] - amounts["total"]) > Decimal("0.01"):
                reasons.append("Arithmetic mismatch: subtotal plus tax must equal total within 0.01")
    return reasons


def duplicate_key(record):
    """Match vendor and invoice number, ignoring case and repeated whitespace."""
    values = [record.get(field) for field in ("vendor_name", "invoice_number")]
    if not all(isinstance(value, str) and value.strip() for value in values):
        return None
    return tuple(" ".join(value.split()).casefold() for value in values)
