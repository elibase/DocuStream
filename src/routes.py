from datetime import datetime, timezone
from io import BytesIO
from pathlib import PurePosixPath

from fastapi import FastAPI, HTTPException, UploadFile
from pydantic import ValidationError
from pypdf import PdfReader

from .main import parse_invoice
from .schema import ExtractedFields, HealthResponse, InvoiceResponse
from .validation.rules import validate_required_fields_and_dates, validate_amounts

app = FastAPI(title="DocFlow AI", version="0.1.0")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def extract_fields(text: str) -> ExtractedFields:
    """Local mock for the sample format; replace with an AI adapter later."""
    parsed = parse_invoice(text)
    return ExtractedFields.model_validate({
        field: parsed.get(field) or None for field in ExtractedFields.model_fields
    })


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()


@app.post("/extract", response_model=InvoiceResponse)
def extract(file: UploadFile):
    """Extract and validate one PDF without saving the upload or detecting duplicates."""
    try:
        filename = PurePosixPath((file.filename or "").replace("\\", "/")).name
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(415, "Upload a PDF file using the file field.")
        payload = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(payload) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "PDF exceeds the 10 MiB upload limit.")
        if not payload:
            raise HTTPException(422, "The uploaded PDF is empty.")
        if b"%PDF-" not in payload[:1024]:
            raise HTTPException(422, "The uploaded file is not a readable PDF.")
        try:
            reader = PdfReader(BytesIO(payload))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            raise HTTPException(422, "PDF is unreadable or encrypted.") from None
        if not text.strip():
            raise HTTPException(422, "PDF contains no extractable text; OCR is not supported.")
        try:
            fields = ExtractedFields.model_validate(extract_fields(text))
        except TimeoutError:
            raise HTTPException(504, "Extraction service timed out.") from None
        except (ValidationError, ValueError):
            raise HTTPException(502, "Extraction service returned invalid structured data.") from None
        except Exception:
            raise HTTPException(502, "Extraction service failed.") from None

        record = {"source_file": filename, **fields.model_dump()}
        reasons = validate_required_fields_and_dates(record) + validate_amounts(record)
        return InvoiceResponse(
            **record, validation_status="NeedsReview" if reasons else "ReadyForReview",
            exception_reasons=reasons, processed_at=datetime.now(timezone.utc),
        )
    finally:
        file.file.close()
