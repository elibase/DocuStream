from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pypdf import PdfWriter
import pytest

from src.routes import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
def pdf():
    return (Path(__file__).resolve().parents[1] / 'sample_data/invoices/invoice_001.pdf').read_bytes()


def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_extract_sample(client, pdf):
    response = client.post('/extract', files={'file': ('invoice.pdf', pdf, 'application/pdf')})
    assert response.status_code == 200
    data = response.json()
    assert data['source_file'] == 'invoice.pdf'
    assert data['invoice_number'] == 'DEMO-2026-001'
    assert data['total'] == '277.42'
    assert data['extraction_status'] == 'Processed'
    assert data['validation_status'] == 'ReadyForReview'
    assert data['exception_reasons'] == []
    assert data['processed_at'].endswith(('Z', '+00:00'))


def test_missing_upload(client):
    assert client.post('/extract').status_code == 422


@pytest.mark.parametrize('filename,payload,status', [
    ('invoice.txt', b'text', 415),
    ('invoice.pdf', b'', 422),
    ('invoice.pdf', b'not a pdf', 422),
    ('invoice.pdf', b'%PDF-1.4\nbroken', 422),
])
def test_invalid_upload(client, filename, payload, status):
    response = client.post('/extract', files={'file': (filename, payload)})
    assert response.status_code == status
    assert response.json()['detail']


def test_size_limit(client, pdf):
    with patch('src.routes.MAX_UPLOAD_BYTES', 10):
        assert client.post('/extract', files={'file': ('invoice.pdf', pdf)}).status_code == 413


def test_blank_and_encrypted_pdfs(client):
    for encrypted in (False, True):
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        if encrypted:
            writer.encrypt('secret')
        stream = BytesIO()
        writer.write(stream)
        assert client.post('/extract', files={'file': ('invoice.pdf', stream.getvalue())}).status_code == 422


def test_business_errors_are_reviewable(client, pdf):
    fields = dict(invoice_number='DEMO-1', vendor_name=None, invoice_date='2026-02-30',
                  currency='CAD', subtotal='10.00', tax='1.30', total='20.00')
    with patch('src.routes.extract_fields', return_value=fields):
        response = client.post('/extract', files={'file': ('invoice.pdf', pdf)})
    assert response.status_code == 200
    assert response.json()['validation_status'] == 'NeedsReview'
    assert len(response.json()['exception_reasons']) == 3


@pytest.mark.parametrize('result,status', [
    (TimeoutError('private detail'), 504),
    (RuntimeError('private detail'), 502),
    ({'total': []}, 502),
])
def test_extractor_errors(client, pdf, result, status):
    options = {'side_effect': result} if isinstance(result, Exception) else {'return_value': result}
    with patch('src.routes.extract_fields', **options):
        response = client.post('/extract', files={'file': ('invoice.pdf', pdf)})
    assert response.status_code == status
    assert 'private detail' not in response.text
