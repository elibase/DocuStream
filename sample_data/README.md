# Fictional invoice samples

`invoices/` contains 12 digital, text-based PDF invoices. All vendors, recipients,
and transactions are fictional. These are sample source documents, not processed results.
`invoice_data.json` contains the corresponding records using all fields in the project invoice data model.
`source_file` is relative to `invoices/`.

- Dates use ISO 8601 (`YYYY-MM-DD`). Two invoices omit the optional due date.
- Currency is CAD. Amounts are decimal strings with two decimal places to preserve precision.
- A fictional 13% tax is applied uniformly for testing. Tax is rounded to the nearest
  cent using decimal ROUND_HALF_UP; total equals subtotal plus rounded tax.
- Extraction and validation statuses and processed_at are null because processing
  has not run. exception_reasons is an empty list, not a validation result.
- All 12 invoice numbers are unique and all totals are arithmetically consistent.

Copy PDFs into the local `input/` folder when ready to process a batch.
