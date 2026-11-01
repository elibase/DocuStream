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
3. **AI extraction** — Send the text to a locally running Ollama model and request structured invoice fields.
4. **Validation** — Apply ordinary code-based rules to check required fields, dates, amounts, arithmetic, and duplicates.
5. **Classification** — Mark records as `ReadyForReview`, `NeedsReview`, or `Failed`.
6. **Output** — Save results to CSV or Excel, move files into appropriate folders, and write processing logs.
7. **Human review** — Leave uncertain, incomplete, or inconsistent records for a person. The bot does not independently authorize payment.

## Suggested Technology Stack

| Component | Suggested technology | Purpose |
|---|---|---|
| RPA orchestration | UiPath Studio | Coordinate the workflow, manage files, call the API, and write outputs |
| Backend API | Python + FastAPI | Expose a document-extraction endpoint |
| AI extraction | Ollama with a local model and JSON-schema structured outputs | Extract fields from invoice text without paid cloud API calls |
| PDF text extraction | pypdf | Read text from digital PDFs |
| OCR (optional) | An OCR tool or service | Read scanned PDFs or images |
| Output | CSV or Excel | Store extracted fields and processing statuses |
| Tests | Python `pytest` | Test validation rules and error cases |
| Version control | Git | Track changes and publish the project |

Ollama is the selected inference runtime. Run a downloaded model locally; this
project will not depend on paid cloud inference or OpenAI API billing. Keep the
extractor behind the existing FastAPI interface so UiPath does not depend on the
model choice. Retain the mocked extractor for automated tests and development.

The development computer has 32 GB of RAM (user reported). Choose the model and
quantization after checking available memory and CPU/GPU capabilities, then measure
extraction accuracy and response times on the fictional invoices. RAM alone does
not establish inference speed. Model selection and installation remain pending.

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

- [x] Create 10–15 fictional sample invoices.
- [x] Set up a local input folder and output folder.
- [x] Extract text from digital PDF invoices.
- [x] Parse a small set of known fields or use mocked AI responses.
- [x] Export the extracted data to CSV.

**Done when:** A batch of sample invoices produces a structured output file.

### Milestone 2 — Validation and exception handling

- [x] Validate required fields and date formats.
- [x] Check arithmetic and monetary values.
- [x] Detect duplicate invoice records.
- [x] Assign processing and validation statuses.
- [x] Log errors and exception reasons.
- [x] Add tests for valid, invalid, duplicate, and unreadable documents.

**Done when:** Invalid records are flagged instead of being silently treated as valid.

### Milestone 3 — AI extraction API

- [x] Create `GET /health` and `POST /extract` FastAPI endpoints.
- [x] Define Pydantic schemas for extracted fields and API responses.
- [x] Implement a mocked extractor using the fictional invoice labels.
- [x] Select Ollama with local inference as the no-paid-API integration approach.
- [x] Install Ollama and download a suitable local model; selected `qwen3:8b` with Q4_K_M quantization.
- [x] Connect the extractor to Ollama using the invoice JSON schema and validate the returned fields with Pydantic.
- [x] Handle upload errors, malformed structured output, and extraction-service exceptions; test timeout and service-error mappings with simulated failures.
- [x] Configure and verify Ollama request timeouts and handling for an unavailable server, missing model, malformed output, and inference errors (automated simulated error tests).
- [x] Configure the Ollama base URL, model, and timeout through environment variables; document defaults in `.env.example`. Local inference does not require a cloud API key; never commit secrets if another provider is added later.
- [x] Test health checks, successful extraction, reviewable business errors, invalid uploads, and simulated extractor failures.
- [x] Test the Ollama adapter with simulated responses and run an actual local-model extraction against the fictional sample invoices.

**Done when:** The API extracts fields using the local Ollama model, returns
schema-validated structured data or clear errors, and passes the existing business
validation and API tests without requiring paid inference.

**Current status:** Milestone 3 is complete. `/extract` uses local `qwen3:8b`
(Q4_K_M) by default, with mock mode retained for offline development. The automated
suite passes 41 tests and 69 subtests. A real local inference run matched all eight
extracted fields for all 12 fictional sample invoices and returned ReadyForReview
for each, taking about 4–4.4 seconds per invoice with the model loaded. These
results cover the current samples, not arbitrary invoice layouts. See
`output/ollama_verification.json` for the local run report and
`docs/Ollama_Setup.md` for configuration and verification instructions.
Duplicate detection remains in the batch workflow, whose CSV command still uses
the deterministic parser. No paid inference or cloud API key is required.

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
- Ollama: https://ollama.com/
- Ollama structured outputs: https://ollama.com/blog/structured-outputs
- Playwright for Python (optional alternative for browser automation): https://playwright.dev/python/

## Future Enhancements

- OCR for scanned invoices
- A small review dashboard
- Database-backed processing history
- Confidence-based review routing, if the extraction service provides a meaningful confidence signal
- Email attachment intake in a test mailbox
- Metrics such as processing time, extraction success rate, and exception rate
