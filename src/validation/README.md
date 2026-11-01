# Invoice validation

Required fields: source_file, invoice_number, vendor_name, invoice_date,
currency, subtotal, tax, and total. Missing keys, null values, and blank strings
fail the presence check. Zero amounts count as present.

invoice_date and any supplied due_date must be actual calendar dates in exactly
YYYY-MM-DD format. due_date is optional. Date ordering is not checked yet.

Amounts must be numeric, finite, non-negative, and representable to two decimal
places, with a maximum of 999999999999.99 per field. Arithmetic uses Decimal;
subtotal plus tax must match total within an inclusive 0.01 tolerance. Tax rates
are not validated. Currency conversion is not performed.

Duplicates are detected within the current batch using vendor_name and
invoice_number, ignoring case and repeated whitespace. Every matching record
is flagged, including the first copy. Different vendors can reuse a number.
Historical duplicate detection across separate batches is not implemented.

The CSV includes:

- required_fields_dates_status: Passed or NeedsReview for just those checks;
  NotChecked when extraction fails.
- extraction_status and processing_status: Processed when text is extracted
  and checked, even if the invoice needs review; Failed otherwise.
- validation_status: ReadyForReview when all implemented checks pass,
  NeedsReview for validation failures, or Failed for extraction/format failures.
  ReadyForReview does not authorize payment.
- exception_reasons: a JSON list of all validation failures or a safe extraction
  error description.
- processed_at: an ISO 8601 timestamp in UTC.

Run `src/main.py` to process files from `input/invoices/`. Unsupported files,
unreadable PDFs, encrypted PDFs that cannot be read, and PDFs with no extractable
text produce failure rows without stopping the batch. Hidden files and directories
are skipped. The sample parser still expects the fictional invoices' label format;
OCR and AI extraction are not implemented.

`output/invoices.csv` is replaced on each run. `output/invoices.log` appends one
JSON entry per file per run, including timestamps, statuses, and exception reasons.
It does not store extracted text or amounts. Re-running the same batch replaces
CSV rows rather than accumulating duplicates; log entries intentionally accumulate.
Output filesystem errors still stop the run.

Run checks from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
