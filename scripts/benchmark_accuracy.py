"""Run parser versus local-model accuracy: python -m scripts.benchmark_accuracy."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import time

from pypdf import PdfReader

from src.extraction.ollama_extractor import extract_fields
from src.main import parse_invoice


FIELDS = ('invoice_number', 'vendor_name', 'invoice_date', 'due_date',
          'currency', 'subtotal', 'tax', 'total')
AMOUNTS = {'subtotal', 'tax', 'total'}


def normalized(field, value):
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    text = str(value).strip()
    if field in AMOUNTS:
        try:
            amount = Decimal(text)
            if amount.is_finite():
                return amount
        except InvalidOperation:
            pass
        return ('invalid_amount', text)
    if field == 'currency':
        return text.upper()
    if field == 'vendor_name':
        return ' '.join(text.split()).casefold()
    # Invoice identifiers and ISO dates must otherwise match exactly.
    return text


def score(expected, actual, error=None):
    return {field: {
        'expected': expected[field], 'actual': actual.get(field),
        'correct': error is None and normalized(field, expected[field]) == normalized(field, actual.get(field)),
    } for field in FIELDS}


def summarize(rows):
    correct = sum(value['correct'] for row in rows for value in row['fields'].values())
    total = len(rows) * len(FIELDS)
    absent = [value for row in rows for value in row['fields'].values() if normalized('due_date', value['expected']) is None]
    present = [value for row in rows for value in row['fields'].values() if normalized('due_date', value['expected']) is not None]
    return dict(invoices=len(rows), correct_fields=correct, total_fields=total,
                field_accuracy=correct / total if total else None,
                present_field_accuracy=sum(v['correct'] for v in present) / len(present) if present else None,
                complete_invoices=sum(all(v['correct'] for v in row['fields'].values()) for row in rows),
                missing_value_correct=sum(v['correct'] for v in absent), missing_value_total=len(absent),
                errors=sum(row['error'] is not None for row in rows),
                average_seconds=sum(row['seconds'] for row in rows) / len(rows) if rows else None,
                per_field={field: dict(correct=sum(row['fields'][field]['correct'] for row in rows), total=len(rows)) for field in FIELDS})


def markdown(report):
    lines = ['# Invoice extraction benchmark', '', f"Generated: {report['generated_at']}", '',
             f"Model: `{report['model']}`. One sequential pass; timings include cold loads if any.", '',
             '| Dataset | Extractor | Field accuracy | Present fields | Complete invoices | Missing values | Errors | Mean seconds |',
             '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for group in report['summary']:
        s = group['metrics']
        lines.append(f"| {group['dataset']} | {group['extractor']} | {s['field_accuracy']:.1%} ({s['correct_fields']}/{s['total_fields']}) | {s['present_field_accuracy']:.1%} | {s['complete_invoices']}/{s['invoices']} | {s['missing_value_correct']}/{s['missing_value_total']} | {s['errors']} | {s['average_seconds']:.3f} |")
    lines += ['', '## Per-field accuracy', '', '| Dataset / extractor | ' + ' | '.join(FIELDS) + ' |',
              '| --- | ' + ' | '.join(['---'] * len(FIELDS)) + ' |']
    for group in report['summary']:
        counts = group['metrics']['per_field']
        lines.append(f"| {group['dataset']} / {group['extractor']} | " + ' | '.join(f"{counts[f]['correct']}/{counts[f]['total']}" for f in FIELDS) + ' |')
    lines += ['', '## Interpretation', '',
              'Both extractors receive identical pypdf text. Only the scorer reads reference answers. '
              'PDF reading time is recorded separately and excluded from extractor timing. '
              'Monetary comparisons use exact Decimal equality (10 and 10.00 are equivalent), '
              'with no arithmetic tolerance. Vendor whitespace/case and currency case are normalized; '
              'dates must match the expected ISO value and invoice identifiers remain case-sensitive. '
              'Null and blank are equivalent. Failed extractions score zero, including absent fields.', '',
              'This is a small synthetic development dataset, not an independent held-out evaluation. '
              'The parser was designed for the original fixed labels; varied labels expose that limitation. '
              'Results demonstrate behavior on these documents, not superiority over all rule-based extractors. '
              'Business-validation success is not used as an accuracy measure. '
              'Inspect per-field expected/actual values and errors in the companion JSON before making claims.', '',
              'Temperature is 0, thinking is disabled, context is 4096 tokens, output budget is 512 tokens. '
              'Latency is a single-run measurement, not a controlled performance benchmark.']
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--datasets', nargs='+', default=['sample_data', 'sample_data/varied_layouts'])
    parser.add_argument('--output', default='output/accuracy_benchmark', help='Report path prefix')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.environ['EXTRACTION_BACKEND'] = 'ollama'
    # Load and validate every reference before starting potentially slow inference.
    cases = []
    fingerprints = []
    for dataset in args.datasets:
        directory = root / dataset
        raw = (directory / 'invoice_data.json').read_bytes()
        references = json.loads(raw)
        if not references:
            raise ValueError(f'Empty reference dataset: {dataset}')
        seen = set()
        for reference in references:
            if not all(field in reference for field in FIELDS):
                raise ValueError(f'Incomplete reference in {dataset}')
            name = reference['source_file']
            if name in seen or Path(name).name != name:
                raise ValueError(f'Duplicate or invalid reference filename: {name}')
            seen.add(name)
            payload = (directory / 'invoices' / name).read_bytes()
            fingerprints.append(dict(dataset=dataset, source_file=name, sha256=hashlib.sha256(payload).hexdigest()))
            cases.append((dataset, reference, directory / 'invoices' / name))
        fingerprints.append(dict(dataset=dataset, reference_sha256=hashlib.sha256(raw).hexdigest()))
    rows = []
    for dataset, reference, path in cases:
        start = time.perf_counter()
        pdf_error = None
        try:
            text = '\n'.join(page.extract_text() or '' for page in PdfReader(path).pages)
            if not text.strip():
                raise ValueError('No text')
        except Exception as error:
            pdf_error = f'PDF extraction failed: {type(error).__name__}'
            text = ''
        pdf_seconds = time.perf_counter() - start
        for name, extractor in [('parser', parse_invoice), ('ollama', lambda text: extract_fields(text).model_dump())]:
            start = time.perf_counter()
            actual, failure = {}, pdf_error
            if failure is None:
                try:
                    actual = extractor(text)
                except Exception as error:
                    failure = f'Extractor failed: {type(error).__name__}'
            row = dict(dataset=dataset, source_file=path.name, extractor=name,
                       seconds=time.perf_counter() - start, pdf_seconds=pdf_seconds,
                       error=failure, fields=score(reference, actual, failure))
            rows.append(row)
            print(f"{dataset}/{path.name} {name}: {sum(v['correct'] for v in row['fields'].values())}/8" + (f' ({failure})' if failure else ''), flush=True)
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row['dataset'], row['extractor'])].append(row)
    report = dict(generated_at=datetime.now(timezone.utc).isoformat(), model=os.getenv('OLLAMA_MODEL', 'qwen3:8b'),
                  base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                  fingerprints=fingerprints, results=rows,
                  summary=[dict(dataset=dataset, extractor=name, metrics=summarize(items)) for (dataset, name), items in grouped.items()])
    prefix = root / args.output
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    prefix.with_suffix('.md').write_text(markdown(report), encoding='utf-8')
    print(f'Reports saved to {prefix}.json and {prefix}.md')
    if any(row['error'] for row in rows):
        raise SystemExit('Benchmark contains extraction errors; see report. Errors remain in accuracy denominators.')


if __name__ == '__main__':
    main()
