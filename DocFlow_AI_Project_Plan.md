# DocFlow AI — AI-Powered Document Processing with RPA

## Project Overview

**DocFlow AI** is a small business-automation project that uses Robotic Process Automation (RPA) and an AI-powered extraction service to process invoice documents.

The goal is to automate repetitive invoice-handling tasks while keeping validation deterministic and routing incomplete or questionable records to a person for review.

This project is intended as a portfolio demonstration of:
- RPA workflow design
- AI-assisted document information extraction
- Python API development
- Business-rule validation
- Exception handling and logging
- Human-in-the-loop review

> **Scope note:** Start with fictional sample invoices and a local test environment. Do not use real customer or financial documents.

## Proposed Workflow

1. **Input documents** — Read PDF invoices from an input folder.
2. **Text extraction** — Extract text from each PDF. Scanned documents may require OCR.
3. **AI extraction** — Send the text to an LLM-backed service and request structured fields.
4. **Validation** — Apply ordinary code-based rules to check required fields, dates, amounts, arithmetic, and duplicates.
5. **Classification** — Mark records as `ReadyForReview`, `NeedsReview`, or `Failed`.
6. **Output** — Save results to CSV or Excel, move files into appropriate folders, and write processing logs.
7. **Human review** — Leave uncertain, incomplete, or inconsistent records for a person. The bot does not independently authorize payment.

## Suggested Technology Stack

| Component | Suggested technology | Purpose |
|---|---|---|
| RPA orchestration | UiPath Studio | Coordinate the workflow, manage files, call the API, and write outputs |
| Backend API | Python + FastAPI | Expose a document-extraction endpoint |
| AI extraction | An LLM API with structured-output support | Extract fields from invoice text |
| PDF text extraction | A Python PDF text-extraction library | Read text from digital PDFs |
| OCR (optional) | An OCR tool or service | Read scanned PDFs or images |
| Output | CSV or Excel | Store extracted fields and processing statuses |
| Tests | Python `pytest` | Test validation rules and error cases |
| Version control | Git | Track changes and publish the project |

The AI provider can be selected later. Keep the extraction service behind an API interface so the provider can be changed without rewriting the whole workflow. A mocked extraction response can be used while building the first version.

## Invoice Data Model

Start with these fields:

- `source_file`
- `invoice_number`
- `vendor_name`
- `invoice_date`
- `due_date` (optional)
- `currency`
- `subtotal`
- `tax`
- `total`
- `extraction_status`
- `validation_status`
- `exception_reasons`
- `processed_at`

Use fictional data and clearly define how currency and rounding are handled.

## Business Rules

The validation layer should use deterministic code rather than asking the AI whether a document is valid.

- Required fields must be present.
- Dates must be parseable and follow the chosen format.
- Monetary values must be numeric and non-negative.
- The subtotal plus tax should equal the total within a defined rounding tolerance.
- Duplicate invoice numbers should be flagged, ideally using vendor name and invoice number together.
- Missing or inconsistent information must be routed to human review.
- Unexpected file formats and unreadable documents must be logged as failures.
- AI output must be parsed and schema-validated before use.

Do not automatically approve or pay invoices. The output should indicate that a record is ready for review, not that payment has been authorized.

## Processing Statuses

| Status | Meaning |
|---|---|
| `ReadyForReview` | Required fields are present and validation rules passed |
| `NeedsReview` | Data is missing, inconsistent, duplicated, or uncertain |
| `Failed` | The file could not be read or processing failed |
| `Processed` | The workflow completed and the result was recorded |

Keep workflow completion separate from invoice validity. For example, an invoice can be successfully processed but still require review.

## Implementation Milestones

### Milestone 1 — Basic document processor

- [ ] Create 10–15 fictional sample invoices.
- [ ] Set up a local input folder and output folder.
- [ ] Extract text from digital PDF invoices.
- [ ] Parse a small set of known fields or use mocked AI responses.
- [ ] Export the extracted data to CSV.

**Done when:** A batch of sample invoices produces a structured output file.

### Milestone 2 — Validation and exception handling

- [ ] Validate required fields and date formats.
- [ ] Check arithmetic and monetary values.
- [ ] Detect duplicate invoice records.
- [ ] Assign processing and validation statuses.
- [ ] Log errors and exception reasons.
- [ ] Add tests for valid, invalid, duplicate, and unreadable documents.

**Done when:** Invalid records are flagged instead of being silently treated as valid.

### Milestone 3 — AI extraction API

- [ ] Create a FastAPI endpoint such as `POST /extract`.
- [ ] Define a Pydantic schema for the expected response.
- [ ] Implement a mocked extractor first.
- [ ] Add the chosen LLM provider after the schema and workflow work.
- [ ] Handle timeouts, malformed output, and API errors.
- [ ] Keep API keys in environment variables; never commit secrets.

**Done when:** The API returns validated structured data or a clear error for a sample document.

### Milestone 4 — UiPath integration

- [ ] Build a UiPath workflow that enumerates input files.
- [ ] Call the extraction API for each document.
- [ ] Validate or consume the API result and record its status.
- [ ] Write results to CSV or Excel.
- [ ] Move or copy files into success, review, and failure folders.
- [ ] Log each document's outcome.
- [ ] Make repeat runs safe so completed records are not duplicated.

**Done when:** UiPath can process a batch from start to finish and produce a traceable result.

### Milestone 5 — Portfolio polish

- [ ] Add a README with setup instructions and an architecture diagram.
- [ ] Include sample input and output files containing fictional data.
- [ ] Capture screenshots or a short demo video.
- [ ] Document known limitations and future improvements.
- [ ] Explain what was implemented versus what remains a prototype.

## Suggested Repository Structure

```text
docflow-ai/
├── README.md
├── sample_data/
│   ├── invoices/
│   └── expected_output.csv
├── src/
│   ├── api/
│   │   ├── main.py
│   │   └── schemas.py
│   ├── extraction/
│   │   └── extractor.py
│   ├── validation/
│   │   └── rules.py
│   └── processing/
│       └── pipeline.py
├── tests/
│   ├── test_validation.py
│   └── test_pipeline.py
├── output/
│   └── .gitkeep
├── requirements.txt
└── .env.example
```

The UiPath project can be stored in a separate `uipath/` directory or in the structure generated by UiPath Studio. Do not commit real `.env` files, API keys, or private documents.

## Reliability and Safety Considerations

- **Human review:** Route uncertain or inconsistent results to a person.
- **No payment authorization:** The prototype only classifies and reports records.
- **Idempotency:** Re-running the workflow should not create duplicate output entries.
- **Logging:** Record timestamps, source file names, statuses, and safe error details.
- **Retries:** Retry temporary failures a limited number of times; avoid infinite retry loops.
- **Privacy:** Use synthetic documents and avoid logging unnecessary sensitive content.
- **AI limitations:** Treat model output as untrusted until it passes schema and business-rule validation.
- **Testing:** Include malformed PDFs, missing fields, duplicate invoices, incorrect totals, and API failures.

## Definition of Done

The initial portfolio version is complete when:

- A batch of fictional invoices can be processed.
- The workflow extracts the intended fields or clearly records extraction failures.
- Validation rules detect common errors and duplicates.
- Results and exception reasons are written to a report.
- UiPath orchestrates the process and calls the Python API.
- Logs make it possible to understand what happened to each file.
- The README explains setup, architecture, testing, limitations, and a demo.

## Resume Bullet (Use Only After Implementing)

> Built an AI-assisted RPA workflow using UiPath and Python/FastAPI to extract invoice data, validate business rules, flag duplicate or incomplete records, and generate processing reports with exception logging and human review.

Adjust this statement to match the features actually completed.

## Useful Starting Resources

- UiPath Studio: https://www.uipath.com/product/studio
- Microsoft Power Automate (alternative RPA platform): https://www.microsoft.com/en-us/power-platform/products/power-automate
- FastAPI: https://fastapi.tiangolo.com/
- Playwright for Python (optional alternative for browser automation): https://playwright.dev/python/

## Future Enhancements

- OCR for scanned invoices
- A small review dashboard
- Database-backed processing history
- Confidence-based review routing, if the extraction service provides a meaningful confidence signal
- Email attachment intake in a test mailbox
- Metrics such as processing time, extraction success rate, and exception rate
