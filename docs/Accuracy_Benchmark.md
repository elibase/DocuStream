# Accuracy benchmark

Start Ollama with `qwen3:8b` installed, then run from the project root:

```powershell
.\.venv\Scripts\python.exe -m scripts.benchmark_accuracy
```

The default run evaluates both extractors on the original 12 invoices and the
12 varied-layout invoices. It calls the local model directly; a running FastAPI
server is not required. It forces `EXTRACTION_BACKEND=ollama` so an environment
setting cannot accidentally benchmark the mock as AI. Model, local URL, and
timeout use the same environment variables as the API.

Output files (replaced each run):

- `output/accuracy_benchmark.md`: accuracy/timing comparison and per-field counts.
- `output/accuracy_benchmark.json`: every expected and actual field, match result,
  extractor error, PDF/text timing, configuration, and PDF/reference SHA-256 hashes.

Run only the varied set or save a different report:

```powershell
.\.venv\Scripts\python.exe -m scripts.benchmark_accuracy --datasets sample_data/varied_layouts --output output/varied_benchmark
```

## How scoring works

Both extractors get the exact same text extracted once per PDF. Reference JSON
is used only by the scorer, not the parser/model. Eight fields are scored:
invoice_number, vendor_name, invoice_date, due_date, currency, subtotal, tax, total.
Filenames and processing statuses are not extraction accuracy targets.

- Field accuracy: correct fields / all expected fields.
- Present-field accuracy: excludes reference values that are absent, avoiding
  inflated scores for returning empty optional fields.
- Complete invoices: all eight fields must be correct.
- Missing-value accuracy: correct absent values / expected absent values.
- Per-field counts: identify weaknesses such as totals or vendor selection.
- Mean extractor time: includes local inference/client overhead and any cold
  model load; excludes PDF reading, which is recorded separately.

Amounts compare using exact Decimal equality, so `10` and `10.00` match but
`10.01` does not. The business-rule rounding tolerance is not used for accuracy.
Vendor case and whitespace, currency case, and blank/null values are normalized.
Dates must match expected ISO dates; invoice identifiers must match case.
No fuzzy matching or answer correction occurs in the scorer.

Errors are recorded and count as incorrect for every field, including optional
absent values. The run continues, writes reports, and exits nonzero if any
extraction error occurred. Incorrect answers alone do not fail the command:
measuring mistakes is the purpose of the benchmark.

## Interpreting results honestly

These are small fictional development sets, not a held-out real-world evaluation.
The baseline parser expects the original labels; the varied set measures the
benefit of handling layouts that baseline does not support. It does not prove
AI beats a parser written specifically for those other layouts. Before publishing
a broad accuracy claim, freeze the prompt/code, create a new unseen set, manually
review the expected answers against PDFs, and record that separate result.

Passing business validation does not establish that the fields are correct.
Review mismatched expected/actual values in JSON. Runtime depends on hardware,
model loading, and context; this single pass is not a controlled latency study.

## Initial measured result

On the first run with `qwen3:8b`:

| Dataset | Parser fields | Qwen fields | Qwen complete invoices |
| --- | --- | --- | --- |
| Original samples | 96/96 (100%) | 96/96 (100%) | 12/12 |
| Varied layouts | 3/96 (3.1%) | 75/96 (78.1%) | 0/12 |

On the varied set Qwen correctly returned invoice numbers, vendors, currencies,
and all monetary fields. All 21 mismatches were date formatting: it copied the
printed dates instead of converting them to the required YYYY-MM-DD representation.
This shows useful field extraction but a remaining output-format limitation;
it does not establish that the model chose the wrong calendar dates. The scorer
deliberately enforces the current API date contract. The parser's three matches
were correctly empty optional due dates, not recovered populated fields.

Mean Qwen times were approximately 4.66 seconds for original samples and 4.17
seconds for varied samples. See the generated report for the measured run rather
than treating these numbers as permanent guarantees.

## Scoring tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_benchmark.py -q -p no:cacheprovider
```

Tests verify normalization boundaries, invented optional values, complete-invoice
counts, and that failed extractions remain in the accuracy denominator. They do
not invoke Ollama. The benchmark itself is an opt-in live evaluation.
