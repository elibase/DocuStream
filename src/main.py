from pypdf import PdfReader
import csv
import json
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

if __package__:
    from .validation.rules import validate_required_fields_and_dates, validate_amounts, duplicate_key
else:
    from validation.rules import validate_required_fields_and_dates, validate_amounts, duplicate_key

FIELD_LABELS = {
    "invoice_number": "Invoice number",
    "vendor_name": "Vendor",
    "bill_to": "Bill to",
    "invoice_date": "Invoice date",
    "due_date": "Due date",
    "currency": "Currency",
    "description": "Description",
    "quantity": "Quantity",
    "subtotal": "Subtotal",
    "tax": "Sample tax (13%)",
    "total": "Total",
}


def parse_invoice(text):
    """Read labeled fields from the fictional sample invoice format."""
    values = {}
    for line in text.splitlines():
        label, separator, value = line.partition(":")
        if separator:
            values[label.strip()] = value.strip()

    record = {field: values.get(label, "") for field, label in FIELD_LABELS.items()}
    # Keep currency in its own column and preserve the printed decimal amounts.
    for field in ("subtotal", "tax", "total"):
        currency_prefix = record["currency"] + " "
        record[field] = record[field].removeprefix(currency_prefix)
    return record


def process_batch(input_folder, output_file):
    """Write a batch snapshot and append a JSON log entry for every input file."""
    input_folder, output_file = Path(input_folder), Path(output_file)
    invoice_files = sorted(path for path in input_folder.iterdir()
                           if path.is_file() and not path.name.startswith("."))

    if not invoice_files:
        raise FileNotFoundError(f"No input files found in {input_folder}")

    records = []
    for invoice_file in invoice_files:
        record = {"source_file": invoice_file.name, **dict.fromkeys(FIELD_LABELS, "")}
        reasons = []
        record["extraction_status"] = "Failed"
        record["processing_status"] = "Failed"
        record["validation_status"] = "Failed"
        record["required_fields_dates_status"] = "NotChecked"
        if invoice_file.suffix.lower() != ".pdf":
            reasons.append("Unsupported file format: expected PDF")
        else:
            try:
                reader = PdfReader(invoice_file)
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
                if not text.strip():
                    raise ValueError("No extractable text")
                record.update(parse_invoice(text))
            except Exception as error:
                # A damaged document must not stop later files. Log the error
                # type without exposing document text or arbitrary error details.
                reasons.append(f"PDF extraction failed ({type(error).__name__}); unreadable, encrypted, or no extractable text")
            else:
                record["extraction_status"] = "Processed"
                record["processing_status"] = "Processed"
                field_reasons = validate_required_fields_and_dates(record)
                record["required_fields_dates_status"] = "NeedsReview" if field_reasons else "Passed"
                reasons.extend(field_reasons)
                reasons.extend(validate_amounts(record))
        record["exception_reasons"] = reasons
        records.append(record)

    counts = Counter(duplicate_key(record) for record in records
                     if record["extraction_status"] == "Processed" and duplicate_key(record) is not None)
    for record in records:
        if record["extraction_status"] == "Processed":
            key = duplicate_key(record)
            if key is not None and counts[key] > 1:
                record["exception_reasons"].append("Duplicate invoice: vendor and invoice number repeat in this batch")
            record["validation_status"] = "NeedsReview" if record["exception_reasons"] else "ReadyForReview"
        record["processed_at"] = datetime.now(timezone.utc).isoformat()

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as file, output_file.with_suffix(".log").open("a", encoding="utf-8") as log:
        writer = csv.DictWriter(file, fieldnames=[
            "source_file", *FIELD_LABELS,
            "required_fields_dates_status", "exception_reasons",
            "extraction_status", "processing_status", "validation_status", "processed_at",
        ])
        writer.writeheader()

        for record in records:
            writer.writerow({**record, "exception_reasons": json.dumps(record["exception_reasons"])})
            log.write(json.dumps({key: record[key] for key in (
                "source_file", "processed_at", "extraction_status", "processing_status",
                "validation_status", "exception_reasons",
            )}) + "\n")

    return records


def main():
    project_root = Path(__file__).resolve().parent.parent
    output_file = project_root / "output" / "invoices.csv"
    records = process_batch(project_root / "input" / "invoices", output_file)

    print(f"Exported {len(records)} invoices to {output_file}")


if __name__ == "__main__":
    main()
