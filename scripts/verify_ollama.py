"""Opt-in live integration check: python -m scripts.verify_ollama."""

import json
import argparse
import os
from pathlib import Path
import time

from fastapi.testclient import TestClient

from src.routes import app


def main():
    parser = argparse.ArgumentParser(description="Compare live Ollama extraction against fictional reference data.")
    parser.add_argument("--dataset", default="sample_data", help="Dataset directory containing invoices/ and invoice_data.json")
    parser.add_argument("--report", default="output/ollama_verification.json")
    args = parser.parse_args()
    os.environ["EXTRACTION_BACKEND"] = "ollama"
    root = Path(__file__).resolve().parents[1]
    dataset = root / args.dataset
    expected = json.loads((dataset / "invoice_data.json").read_text())
    results = []
    with TestClient(app) as client:
        for reference in expected:
            path = dataset / "invoices" / reference["source_file"]
            started = time.monotonic()
            response = client.post("/extract", files={"file": (path.name, path.read_bytes(), "application/pdf")})
            data = response.json()
            fields = ("invoice_number", "vendor_name", "invoice_date", "due_date", "currency", "subtotal", "tax", "total")
            result = dict(source_file=path.name, http_status=response.status_code,
                          validation_status=data.get("validation_status"),
                          seconds=round(time.monotonic() - started, 2),
                          mismatched_fields=[field for field in fields if data.get(field) != reference[field]])
            results.append(result)
            print(json.dumps(result), flush=True)
    report = root / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(results, indent=2) + "\n")
    if not all(r["http_status"] == 200 and r["validation_status"] == "ReadyForReview"
               and not r["mismatched_fields"] for r in results):
        raise SystemExit(f"Live sample verification failed; inspect {report}")
    print(f"Verified all {len(results)} sample invoices against reference fields.")


if __name__ == "__main__":
    main()
