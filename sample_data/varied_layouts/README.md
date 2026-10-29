# Varied fictional invoice layouts

12 digital PDFs, using four layouts (three invoices per layout). Every party,
transaction, reference, and address is fictional. No payment is requested.
The original simple sample invoices are preserved in `sample_data/invoices/`.

| Layout | Files | Extraction challenge |
| --- | --- | --- |
| Two-column supplier invoice | 001, 005, 009 | Supplier versus customer, Invoice # versus purchase order, unrelated prior balance |
| Letter-style service invoice | 002, 006, 010 | Billing reference, settlement deadline, fees before tax, written month dates |
| Compact invoice | 003, 007, 011 | Bill No., YYYY/MM/DD dates, denomination, net/gross labels, no optional due date |
| Two-page purchase invoice | 004, 008, 012 | Line items on page one, totals on page two, unrelated credit limit, USD and zero tax |

Each invoice has two line items with quantities, unit prices, and extended amounts.
CAD examples use a fictional 13% sample tax; USD examples use zero tax. These are
test conventions, not real tax guidance. Arithmetic uses Decimal and ROUND_HALF_UP
to the nearest cent. All totals are consistent and all invoice numbers are unique.

`invoice_data.json` holds expected answers using the project invoice model. Dates
are normalized to YYYY-MM-DD and amounts are decimal strings with two fractional
digits. Processing fields remain null because these records are reference data.
`layouts.json` maps filenames to layout names and page counts. Neither reference
file is supplied to the model during extraction.

These samples challenge the original fixed-label parser and are intended for
measuring AI extraction, not for claiming an accuracy improvement in advance.
They contain selectable text; they do not test OCR, scans, or malformed documents.

Try individual files using POST /extract in the API docs. To run the real model
against all varied invoices, from the project root:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_ollama --dataset sample_data/varied_layouts --report output/ollama_varied_verification.json
```

The command checks exact reference field values and review status. A nonzero exit
means at least one result differs; inspect the JSON report before changing code.
The varied set has not been certified as correctly extracted by the model merely
because the PDFs have been generated.

Regenerate the dataset with:

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_varied_invoices
```

This replaces the generated varied PDFs and reference files.
