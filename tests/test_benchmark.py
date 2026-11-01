from scripts.benchmark_accuracy import FIELDS, normalized, score, summarize


def test_normalization_does_not_hide_wrong_values():
    assert normalized('total', '10') == normalized('total', '10.00')
    assert normalized('total', '10.01') != normalized('total', '10.00')
    assert normalized('vendor_name', ' Demo  Vendor ') == normalized('vendor_name', 'demo vendor')
    assert normalized('due_date', '') == normalized('due_date', None)
    assert normalized('invoice_date', '01/02/2026') != normalized('invoice_date', '2026-02-01')
    assert normalized('invoice_number', 'abc') != normalized('invoice_number', 'ABC')
    assert normalized('total', 'NaN') != normalized('total', '10')


def test_scoring_missing_and_invented_values():
    expected = dict.fromkeys(FIELDS, 'value')
    expected['due_date'] = None
    actual = expected.copy()
    actual['invoice_number'] = 'wrong'
    actual['due_date'] = '2026-01-01'
    fields = score(expected, actual)
    assert sum(v['correct'] for v in fields.values()) == 6
    assert not fields['due_date']['correct']


def test_failures_stay_in_denominator_and_do_not_get_null_credit():
    expected = dict.fromkeys(FIELDS, None)
    rows = [dict(fields=score(expected, expected), error=None, seconds=1),
            dict(fields=score(expected, {}, 'timeout'), error='timeout', seconds=3)]
    result = summarize(rows)
    assert result['field_accuracy'] == 0.5
    assert result['complete_invoices'] == 1
    assert result['errors'] == 1
    assert result['missing_value_correct'] == 8
    assert result['missing_value_total'] == 16
    assert result['average_seconds'] == 2
