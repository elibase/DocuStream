from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ExtractedFields(BaseModel):
    """Raw field strings allow invalid business values to be sent for review."""

    model_config = ConfigDict(extra="forbid", strict=True)

    invoice_number: str | None = None
    vendor_name: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    currency: str | None = None
    subtotal: str | None = None
    tax: str | None = None
    total: str | None = None


class InvoiceResponse(ExtractedFields):
    source_file: str
    extraction_status: Literal["Processed"] = "Processed"
    validation_status: Literal["ReadyForReview", "NeedsReview"]
    exception_reasons: list[str] = Field(default_factory=list)
    processed_at: datetime

