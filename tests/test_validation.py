import unittest

from src.validation.rules import REQUIRED_FIELDS, validate_required_fields_and_dates


class RequiredFieldsAndDatesTests(unittest.TestCase):
    def setUp(self):
        self.record = dict(
            source_file="invoice.pdf", invoice_number="DEMO-001", vendor_name="Demo Vendor",
            invoice_date="2024-02-29", currency="CAD", subtotal="10.00", tax="0.00", total="10.00",
        )

    def test_valid_record_and_optional_due_date(self):
        for due in (None, "", "   ", "2024-03-30"):
            with self.subTest(due=due):
                self.assertEqual(validate_required_fields_and_dates({**self.record, "due_date": due}), [])
        self.assertEqual(validate_required_fields_and_dates(self.record), [])

    def test_each_required_field_must_be_present_and_nonblank(self):
        for field in REQUIRED_FIELDS:
            for value in (None, "", "  "):
                with self.subTest(field=field, value=value):
                    record = {**self.record, field: value}
                    self.assertIn(f"Missing required field: {field}", validate_required_fields_and_dates(record))
            record = self.record.copy()
            del record[field]
            self.assertIn(f"Missing required field: {field}", validate_required_fields_and_dates(record))

    def test_zero_amounts_are_present(self):
        self.assertEqual(validate_required_fields_and_dates({**self.record, "subtotal": 0, "tax": 0, "total": 0}), [])

    def test_invalid_dates_in_either_date_field(self):
        for field in ("invoice_date", "due_date"):
            for value in ("2025-02-29", "2026-04-31", "2026-13-01", "0000-01-01",
                          "10/01/2026", "2026-1-01", "20261001", "2026-10-01T00:00:00",
                          " 2026-10-01 ", 20261001):
                with self.subTest(field=field, value=value):
                    reasons = validate_required_fields_and_dates({**self.record, field: value})
                    self.assertEqual(len(reasons), 1)
                    self.assertIn(field, reasons[0])

    def test_collects_multiple_failures_without_duplicate_missing_date_error(self):
        reasons = validate_required_fields_and_dates({**self.record, "vendor_name": "", "invoice_date": None, "due_date": "bad"})
        self.assertEqual(len(reasons), 3)


if __name__ == "__main__":
    unittest.main()
