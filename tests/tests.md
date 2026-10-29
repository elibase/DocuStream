# Running and understanding the tests

Run these PowerShell commands from the project root (the directory containing
`requirements.txt`). The tests use Python's built-in `unittest` framework and
the project's installed dependencies, including `pypdf`. No pytest installation
or running API server is required.

## Run all tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

This uses the project virtual environment directly; activation is optional.
If you have not set up the environment yet:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run one test file

Required-field and date checks:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_validation.py -v
```

Amount, duplicate, and batch-processing checks:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_milestone2.py -v
```

To run only tests whose names contain a particular phrase, add `-k`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v -k invalid_dates
```

## What each test checks

### `test_validation.py`

These tests call `validate_required_fields_and_dates()` in
`src/validation/rules.py` with invoice dictionaries.

| Test | What it verifies |
| --- | --- |
| `test_valid_record_and_optional_due_date` | A valid record, including a leap-day invoice date, passes. The optional due date may be omitted, null, blank, or a valid date. |
| `test_each_required_field_must_be_present_and_nonblank` | Every required field is rejected when missing, null, empty, or whitespace-only. |
| `test_zero_amounts_are_present` | Numeric zero counts as a supplied amount rather than a missing value. |
| `test_invalid_dates_in_either_date_field` | Both date fields reject impossible dates, invalid leap days, incorrect formats, timestamps, surrounding whitespace, and numeric values. |
| `test_collects_multiple_failures_without_duplicate_missing_date_error` | Multiple problems are returned together; a missing invoice date does not also produce an invalid-date error. |

### `test_milestone2.py`

`AmountTests` exercises `validate_amounts()` and `duplicate_key()` in
`src/validation/rules.py`.

| Test | What it verifies |
| --- | --- |
| `test_invalid_amounts` | Each monetary field rejects negatives, NaN, infinity, nonnumeric text, fractions smaller than a cent, amounts above the configured maximum, and booleans. |
| `test_decimal_arithmetic_and_tolerance` | Decimal arithmetic accepts correct totals and a one-cent difference, rejects a two-cent difference, and accepts zero amounts. |
| `test_duplicate_identity` | Vendor and invoice number comparisons ignore case and repeated whitespace. Different vendors produce different identities; a missing vendor produces no duplicate key. |

`BatchTests` calls `process_batch()` in `src/main.py` using real PDF fixtures
created during the tests.

| Test | What it verifies |
| --- | --- |
| `test_mixed_batch_and_rerun` | A seven-file batch contains one valid invoice, two duplicates, one invoice with missing vendor/invalid date/incorrect total, one damaged PDF, one unsupported text file, and one blank PDF. Checks expected statuses and reasons, continued processing after failures, seven CSV rows, UTC timestamps, and log entries without a raw text field. A second run replaces the CSV rows while appending another seven log entries. Hidden `.gitkeep` is ignored. |
| `test_empty_input_does_not_replace_existing_output` | An empty input directory raises `FileNotFoundError` and preserves an existing output file. |

The batch tests use temporary directories that are cleaned up automatically.
They do not modify your local `input/` files or `output/invoices.csv` and do not
need the 12 repository sample invoices.

## Reading the results

The current suite contains 10 test methods. Several methods use `subTest()` to
check multiple values, so more than 10 individual cases are exercised.
A successful full run ends with output similar to:

```text
Ran 10 tests in ...

OK
```

`FAIL` indicates that an assertion did not match the expected behavior. `ERROR`
indicates an unexpected exception or setup/import problem. Read the traceback
and any subtest values to identify the failing case.

The deliberately damaged PDF may cause pypdf to print `EOF marker not found`.
That diagnostic is expected in this fixture; the final unittest result determines
whether the failure-handling test passed.

## Current coverage limits

These tests cover the milestone 2 validation and local batch workflow. They do
not test FastAPI routes, external AI services, OCR, historical duplicate detection,
or every possible PDF layout. The parser currently expects the fictional sample
invoice labels. `ReadyForReview` indicates the implemented checks passed; it does
not authorize payment.
