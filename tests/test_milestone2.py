import csv
import json
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from src.main import process_batch
from src.validation.rules import duplicate_key, validate_amounts


def write_invoice(path, text):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                             NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
    stream = DecodedStreamObject()
    lines = [line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)') for line in text.splitlines()]
    stream.set_data(('BT /F1 12 Tf 50 750 Td 20 TL\n' + '\n'.join(f'({line}) Tj T*' for line in lines) + '\nET').encode('ascii'))
    page[NameObject('/Contents')] = writer._add_object(stream)
    writer.write(path)


class AmountTests(unittest.TestCase):
    def test_invalid_amounts(self):
        for field in ('subtotal', 'tax', 'total'):
            for value in ('-1', 'NaN', 'Infinity', 'abc', '1.001', '1000000000000', True):
                with self.subTest(field=field, value=value):
                    record = dict(subtotal='10.00', tax='1.30', total='11.30')
                    record[field] = value
                    self.assertTrue(validate_amounts(record))

    def test_decimal_arithmetic_and_tolerance(self):
        self.assertEqual(validate_amounts(dict(subtotal='0.10', tax='0.20', total='0.30')), [])
        self.assertEqual(validate_amounts(dict(subtotal='10', tax='1.30', total='11.31')), [])
        self.assertTrue(validate_amounts(dict(subtotal='10', tax='1.30', total='11.32')))
        self.assertEqual(validate_amounts(dict(subtotal=0, tax=0, total=0)), [])

    def test_duplicate_identity(self):
        self.assertEqual(duplicate_key(dict(vendor_name=' Demo  Vendor ', invoice_number='ABC-1')),
                         duplicate_key(dict(vendor_name='demo vendor', invoice_number='abc-1')))
        self.assertNotEqual(duplicate_key(dict(vendor_name='Other', invoice_number='ABC-1')),
                            duplicate_key(dict(vendor_name='Demo', invoice_number='ABC-1')))
        self.assertIsNone(duplicate_key(dict(vendor_name='', invoice_number='ABC-1')))


class BatchTests(unittest.TestCase):
    def test_mixed_batch_and_rerun(self):
        text = ('Invoice number: DEMO-1\nVendor: Fictional Vendor\nInvoice date: 2026-10-01\n'
                'Currency: CAD\nSubtotal: CAD 10.00\nSample tax (13%): CAD 1.30\nTotal: CAD 11.30')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = root / 'input'
            inputs.mkdir()
            write_invoice(inputs / 'valid.pdf', text.replace('DEMO-1', 'DEMO-2'))
            write_invoice(inputs / 'duplicate_a.pdf', text)
            write_invoice(inputs / 'duplicate_b.PDF', text.replace('Fictional Vendor', 'fictional vendor'))
            write_invoice(inputs / 'invalid.pdf', text.replace('DEMO-1', 'DEMO-3').replace('2026-10-01', '2026-02-30').replace('CAD 11.30', 'CAD 20.00').replace('Vendor: Fictional Vendor', 'Vendor:'))
            (inputs / 'broken.pdf').write_bytes(b'%PDF-1.4\nnot a readable PDF')
            (inputs / 'unsupported.txt').write_text('not an invoice')
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            writer.write(inputs / 'blank.pdf')
            (inputs / '.gitkeep').touch()
            output = root / 'output' / 'invoices.csv'
            for run in (1, 2):
                records = process_batch(inputs, output)
                by_name = {r['source_file']: r for r in records}
                self.assertEqual(len(records), 7)
                self.assertEqual(by_name['valid.pdf']['validation_status'], 'ReadyForReview')
                for name in ('duplicate_a.pdf', 'duplicate_b.PDF'):
                    self.assertEqual(by_name[name]['validation_status'], 'NeedsReview')
                    self.assertIn('Duplicate invoice', by_name[name]['exception_reasons'][0])
                invalid = by_name['invalid.pdf']
                self.assertEqual(invalid['processing_status'], 'Processed')
                self.assertEqual(invalid['validation_status'], 'NeedsReview')
                self.assertEqual(len(invalid['exception_reasons']), 3)
                for name in ('broken.pdf', 'unsupported.txt', 'blank.pdf'):
                    self.assertEqual(by_name[name]['validation_status'], 'Failed')
                    self.assertEqual(by_name[name]['extraction_status'], 'Failed')
                    self.assertTrue(by_name[name]['exception_reasons'])
                with output.open(newline='', encoding='utf-8') as file:
                    rows = list(csv.DictReader(file))
                self.assertEqual(len(rows), 7)
                self.assertTrue(all(row['processed_at'].endswith('+00:00') for row in rows))
                logs = [json.loads(line) for line in output.with_suffix('.log').read_text().splitlines()]
                self.assertEqual(len(logs), 7 * run)
                self.assertTrue(all('text' not in entry and entry['processed_at'] for entry in logs))

    def test_empty_input_does_not_replace_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = root / 'input'
            inputs.mkdir()
            output = root / 'invoices.csv'
            output.write_text('previous output')
            with self.assertRaises(FileNotFoundError):
                process_batch(inputs, output)
            self.assertEqual(output.read_text(), 'previous output')


if __name__ == '__main__':
    unittest.main()
