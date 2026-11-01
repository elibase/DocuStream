# Ollama setup on Windows

There are two separate installations:

- The Ollama Windows runtime runs local models and provides the local HTTP API.
- The `ollama` Python package is the client, pinned in `requirements.txt` and
  installed in the project's `.venv`. Installing requirements does not install
  the Windows runtime or download a model.

To install the runtime on another computer:

```powershell
winget install --id Ollama.Ollama --exact
```

Alternatively, use the official installer: https://ollama.com/download/windows

Open a new terminal after installation and verify:

```powershell
ollama --version
ollama list
```

If the server is not running, start it with `ollama serve` in a separate terminal.
The default local API address is `http://localhost:11434`.

To install the Python dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The selected model is `qwen3:8b` (Q4_K_M quantization). Download it if needed:

```powershell
ollama pull qwen3:8b
```

The API now uses Ollama by default. From the project root:

```powershell
$env:EXTRACTION_BACKEND = "ollama"
$env:OLLAMA_BASE_URL = "http://localhost:11434"
$env:OLLAMA_MODEL = "qwen3:8b"
$env:OLLAMA_TIMEOUT_SECONDS = "120"
.\.venv\Scripts\python.exe -m uvicorn src.routes:app --reload
```

These values are the defaults; setting them is optional. `.env.example` documents
them, but `.env` files are not automatically loaded. To use an env file with
uvicorn, install python-dotenv separately and use `--env-file .env`; setting shell
environment variables requires no additional package.

Local inference does not require a cloud API key or paid subscription. The
adapter restricts the server URL to local HTTP loopback addresses and rejects
cloud model tags. Requests disable thinking and use schema-constrained JSON,
temperature 0, a 4096-token context, and a 512-token output budget. Long documents
may need a larger context or chunking in a future iteration; the 10 MiB upload
limit is not a guarantee that an entire document fits the model context.

Set `EXTRACTION_BACKEND=mock` to use the original labeled-field parser for offline
development. Automated tests mock inference and do not require a running server.
The local batch CSV command still uses its deterministic parser; Ollama extraction
is connected to the FastAPI `/extract` endpoint.

Troubleshooting:

- HTTP 503: check that Ollama is running, that `ollama list` includes the configured
  model, and that environment configuration is valid.
- HTTP 504: the Ollama client timed out. The timeout is an HTTP operation timeout,
  not a hard deadline that cancels inference on the server. Cold model loads can
  take longer; adjust the timeout if necessary.
- HTTP 502: inference failed, output was incomplete, or output did not match the
schema. No fallback silently replaces failed model extraction.

The adapter removes an exact matching currency-code prefix from returned amounts
(for example, `CAD 1200.00` becomes `1200.00`). It never fixes arithmetic.

Run the opt-in live sample check from the project root:

```powershell
.\.venv\Scripts\python.exe -m scripts.verify_ollama
```

This sends the 12 fictional PDFs through the in-process FastAPI application and
real local model, compares the eight extracted fields with `invoice_data.json`,
and saves statuses, timings, and mismatched field names to
`output/ollama_verification.json`. It does not change the batch CSV. It requires
a running Ollama server and is separate from automated pytest tests.
