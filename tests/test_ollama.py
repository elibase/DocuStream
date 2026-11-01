import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import ollama
import pytest

from src.extraction.ollama_extractor import extract_fields, ExtractionUnavailable


@pytest.fixture
def runtime(monkeypatch):
    monkeypatch.setenv('EXTRACTION_BACKEND', 'ollama')
    monkeypatch.setenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    monkeypatch.setenv('OLLAMA_MODEL', 'qwen3:8b')
    monkeypatch.setenv('OLLAMA_TIMEOUT_SECONDS', '120')
    with patch('src.extraction.ollama_extractor.ollama.Client') as factory:
        client = MagicMock()
        factory.return_value = client
        client.chat.return_value = SimpleNamespace(done=True, done_reason='stop',
            message=SimpleNamespace(content=json.dumps({'invoice_number': 'DEMO-1', 'total': '1.00'})))
        yield factory, client


def test_structured_local_request(runtime):
    factory, client = runtime
    assert extract_fields('invoice text').total == '1.00'
    factory.assert_called_once_with(host='http://localhost:11434', timeout=120, trust_env=False)
    request = client.chat.call_args.kwargs
    assert request['model'] == 'qwen3:8b'
    assert request['think'] is False and request['stream'] is False
    assert 'total' in request['format']['properties']
    assert request['messages'][1]['content'] == 'invoice text'
    client.close.assert_called_once()


def test_currency_prefix_cleanup_preserves_amounts(runtime):
    runtime[1].chat.return_value.message.content = json.dumps({
        'currency': 'CAD', 'subtotal': 'CAD 1200.00', 'tax': 'CAD 156.00',
        'total': 'CAD 999.00',
    })
    fields = extract_fields('text')
    assert fields.subtotal == '1200.00'
    assert fields.tax == '156.00'
    assert fields.total == '999.00'  # An incorrect printed total is not repaired.


@pytest.mark.parametrize('error,expected', [
    (httpx.ReadTimeout('private'), TimeoutError),
    (ConnectionError('private'), ExtractionUnavailable),
    (httpx.ConnectError('private'), ExtractionUnavailable),
    (ollama.ResponseError('private', status_code=404), ExtractionUnavailable),
    (ollama.ResponseError('private', status_code=500), RuntimeError),
])
def test_provider_errors(runtime, error, expected):
    _, client = runtime
    client.chat.side_effect = error
    with pytest.raises(expected) as caught:
        extract_fields('text')
    assert 'private' not in str(caught.value)
    client.close.assert_called_once()


@pytest.mark.parametrize('content,done,reason', [
    ('not json', True, 'stop'), ('{"total": 10}', True, 'stop'),
    ('{}', False, None), ('{}', True, 'length'), ('', True, 'stop'),
])
def test_invalid_or_incomplete_output(runtime, content, done, reason):
    runtime[1].chat.return_value = SimpleNamespace(done=done, done_reason=reason,
        message=SimpleNamespace(content=content))
    with pytest.raises(ValueError):
        extract_fields('text')


@pytest.mark.parametrize('name,value', [
    ('OLLAMA_BASE_URL', 'https://ollama.com'), ('OLLAMA_MODEL', 'qwen3:cloud'),
    ('OLLAMA_TIMEOUT_SECONDS', '0'), ('OLLAMA_TIMEOUT_SECONDS', 'NaN'),
    ('EXTRACTION_BACKEND', 'unknown'),
])
def test_bad_configuration(runtime, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ExtractionUnavailable):
        extract_fields('text')
    runtime[0].assert_not_called()
