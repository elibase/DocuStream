# Local API

From the project root, install requirements and start the server:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn src.routes:app --reload
```

Open http://127.0.0.1:8000/docs to try the endpoints interactively.

- `GET /health` returns `{"status":"ok"}`. This checks API availability, not AI-provider connectivity.
- `POST /extract` accepts one PDF as the multipart field `file`, up to 10 MiB
  of file content. It returns the invoice model fields, extraction status,
  validation status, exception reasons, and a UTC processing timestamp.

```powershell
curl.exe -F "file=@sample_data/invoices/invoice_001.pdf" http://127.0.0.1:8000/extract
```

Extraction defaults to the local Ollama `qwen3:8b` model. Start Ollama and download
the model before calling `/extract`; see `../docs/Ollama_Setup.md` for configuration.
Set `EXTRACTION_BACKEND=mock` to use the sample-label parser instead.
No cloud credentials are needed. Amounts and dates are returned as raw
strings (or null when missing) so invalid business values can be reviewed.
Pydantic validates the structure, and deterministic rules check business values.

HTTP 200 includes ReadyForReview or NeedsReview. Missing uploads, invalid PDFs,
encrypted PDFs that cannot be read, and PDFs without text return 422. Unsupported
extensions return 415; oversized file content returns 413. The extraction adapter
maps timeout errors to 504 and malformed structured results or service failures
to 502. An unavailable Ollama server, missing model, or invalid configuration
returns 503. The client has a configurable timeout (120 seconds by default).
`GET /health` remains a liveness check even when Ollama is unavailable.

Uploads are not saved, and API calls do not write the batch CSV or log.
The single-file API does not detect duplicates; batch duplicate checks remain
in process_batch(). ReadyForReview does not authorize payment.

Run the complete test suite (including API tests) with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

The API tests require pytest and httpx. unittest discovery still runs the
existing unittest classes but does not discover the pytest API test functions.
