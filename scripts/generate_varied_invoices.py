"""Generate fictional text PDFs with four layouts; no extra dependencies."""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path


class PDF:
    def __init__(self):
        self.pages = []
        self.commands = []

    def text(self, x, y, value, size=11, bold=False):
        escaped = str(value).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        self.commands.append(f"0.10 0.16 0.22 rg BT /{'F2' if bold else 'F1'} {size} Tf {x} {y} Td ({escaped}) Tj ET")

    def line(self, y):
        self.commands.append(f'0.65 0.72 0.78 RG 0.6 w 42 {y} m 570 {y} l S')

    def band(self, y, height):
        self.commands.append(f'0.91 0.95 0.97 rg 42 {y} 528 {height} re f')

    def page(self):
        self.pages.append('\n'.join(self.commands).encode('ascii'))
        self.commands = []

    def save(self, path):
        self.page()
        objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'',
                   b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
                   b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>']
        kids = []
        for stream in self.pages:
            page_id = len(objects) + 1
            kids.append(f'{page_id} 0 R')
            objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {page_id + 1} 0 R >>'.encode())
            objects.append(f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'\nendstream')
        objects[1] = f'<< /Type /Pages /Kids [{" ".join(kids)}] /Count {len(kids)} >>'.encode()
        data = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        offsets = [0]
        for index, obj in enumerate(objects, 1):
            offsets.append(len(data))
            data.extend(f'{index} 0 obj\n'.encode() + obj + b'\nendobj\n')
        start = len(data)
        data.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
        for offset in offsets[1:]:
            data.extend(f'{offset:010d} 00000 n \n'.encode())
        data.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n'.encode())
        path.write_bytes(data)


def footer(pdf, page='1 / 1'):
    pdf.line(68)
    pdf.text(42, 50, 'FICTIONAL TEST DOCUMENT - All parties and transactions are invented.', 8)
    pdf.text(42, 37, 'No payment requested. Not a tax document.', 8)
    pdf.text(515, 37, page, 8)


def items(pdf, entries, y=455):
    pdf.band(y - 5, 23)
    for x, label in [(50, 'Description'), (340, 'Qty'), (395, 'Unit price'), (505, 'Amount')]:
        pdf.text(x, y + 3, label, 10, True)
    for description, quantity, price in entries:
        y -= 30
        pdf.text(50, y, description, 10)
        pdf.text(345, y, quantity, 10)
        pdf.text(400, y, f'{price:.2f}', 10)
        pdf.text(505, y, f'{quantity * price:.2f}', 10)
    pdf.line(y - 15)


def main():
    root = Path(__file__).resolve().parents[1] / 'sample_data/varied_layouts'
    folder = root / 'invoices'
    folder.mkdir(parents=True, exist_ok=True)
    records, manifest = [], []
    vendors = ['Moss Lantern Supply', 'Azure Finch Consulting', 'Orchard Comet Services',
               'Copper Willow Studio', 'Frost Kite Logistics', 'Amber Harbor IT',
               'Indigo Fern Printworks', 'Birch Otter Workshop', 'Violet Cedar Rentals',
               'Silver Meadow Systems', 'Golden Prism Design', 'Pine Sparrow Training']
    for index, vendor in enumerate(vendors, 1):
        layout = (index - 1) % 4
        issued = date(2026, 9, index)
        due = issued + timedelta(days=30) if index not in (3, 7, 11) else None
        currency = 'USD' if index in (4, 8, 12) else 'CAD'
        rate = Decimal('0.00') if currency == 'USD' else Decimal('0.13')
        entries = [('Document workflow configuration', 2, Decimal('125.25') + index),
                   ('Template setup and handover', 1, Decimal('75.50') + index)]
        subtotal = sum(qty * price for _, qty, price in entries)
        tax = (subtotal * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total = subtotal + tax
        number = f'VAR-{index:03d}-2026'
        filename = f'varied_invoice_{index:03d}.pdf'
        record = dict(source_file=filename, invoice_number=number, vendor_name=vendor,
                      invoice_date=issued.isoformat(), due_date=due.isoformat() if due else None,
                      currency=currency, subtotal=str(subtotal), tax=str(tax), total=str(total),
                      extraction_status=None, validation_status=None, exception_reasons=[], processed_at=None)
        records.append(record)
        pdf = PDF()
        if layout == 0:
            name = 'Two-column supplier invoice'
            pdf.band(687, 65)
            pdf.text(50, 721, vendor, 20, True)
            pdf.text(50, 698, 'Supplier | 18 Example Grove, Demo City', 9)
            pdf.text(42, 651, 'INVOICE', 23, True)
            pdf.text(350, 655, f'Invoice #: {number}', 12, True)
            pdf.text(350, 630, f'Issued: {issued:%B %d, %Y}')
            pdf.text(350, 607, f'Pay by: {due:%B %d, %Y}')
            pdf.text(42, 575, 'BILL TO', 10, True)
            pdf.text(42, 553, 'Demo Document Lab')
            pdf.text(42, 532, 'Purchase order: PO-8801 (not the invoice number)', 9)
            items(pdf, entries)
            for y, label, value in [(280, 'Net charges', subtotal), (255, 'Tax - 13%', tax), (215, 'Invoice total', total)]:
                pdf.text(335, y, label, 11, True)
                pdf.text(485, y, f'{value:.2f}', 12)
            pdf.text(42, 180, f'All amounts in {currency}. Terms: net 30.')
            pdf.text(42, 155, 'Previous account balance: 46.00 (excluded from this invoice)', 9)
        elif layout == 1:
            name = 'Letter-style service invoice'
            pdf.text(42, 733, 'SERVICE INVOICE', 24, True)
            pdf.text(42, 692, f'From: {vendor}', 16, True)
            pdf.line(674)
            pdf.text(42, 645, 'To: Demo Document Lab - Accounts Team')
            pdf.text(42, 616, f'Our billing reference: {number}')
            pdf.text(42, 590, f'Document date: {issued:%d %b %Y}')
            pdf.text(42, 564, f'Settlement deadline: {due:%d %b %Y}')
            pdf.text(42, 525, 'Services delivered under project DEMO-742. Thank you for your business.')
            items(pdf, entries, 470)
            pdf.text(42, 322, f'Fees before tax ({currency}): {subtotal:.2f}')
            pdf.text(42, 295, f'Applicable sample tax ({currency}): {tax:.2f}')
            pdf.band(231, 42)
            pdf.text(50, 247, f'Total for this invoice: {currency} {total:.2f}', 15, True)
            pdf.text(42, 185, 'Customer account: DEMO-300 (not an invoice identifier)', 9)
        elif layout == 2:
            name = 'Compact invoice with optional due date omitted'
            pdf.text(42, 735, vendor, 23, True)
            pdf.text(42, 707, 'ISSUER / FICTIONAL SERVICE PROVIDER', 9)
            pdf.band(630, 52)
            pdf.text(50, 658, f'Bill No. {number}', 15, True)
            pdf.text(50, 639, f'Billed on {issued:%Y/%m/%d}  |  Denomination: {currency}', 10)
            pdf.text(42, 598, 'Customer: Demo Document Lab')
            pdf.text(42, 570, 'Payment terms: payable on receipt; no fixed due date specified.', 10)
            items(pdf, entries, 505)
            pdf.text(42, 346, f'Net: {subtotal:.2f}    +    VAT / tax: {tax:.2f}', 12)
            pdf.text(42, 304, f'Gross amount ({currency}) {total:.2f}', 18, True)
            pdf.text(42, 252, 'Delivery note: DN-00923 (not the bill number)', 10)
        else:
            name = 'Two-page purchase invoice with totals on page two'
            pdf.text(42, 737, 'PURCHASE INVOICE', 24, True)
            pdf.text(42, 694, f'Sold by: {vendor}', 16, True)
            pdf.text(42, 663, 'Sold to: Demo Document Lab')
            pdf.text(42, 620, f'Invoice ID {number}', 13, True)
            pdf.text(42, 590, f'Billing date {issued:%d %B %Y}')
            pdf.text(42, 562, f'Due on {due:%d %B %Y}')
            pdf.text(42, 530, f'Currency for every line: {currency}')
            items(pdf, entries, 470)
            pdf.text(42, 305, 'Summary and final invoice total appear on page 2.', 12, True)
            footer(pdf, '1 / 2')
            pdf.page()
            pdf.text(42, 735, 'INVOICE SUMMARY', 24, True)
            pdf.text(42, 695, f'{vendor} | {number}', 13)
            pdf.text(42, 650, 'Customer: Demo Document Lab')
            for y, label, amount in [(550, 'Merchandise / services total', subtotal), (510, 'Sample tax (0%)', tax), (450, 'TOTAL INVOICE VALUE', total)]:
                pdf.text(42, y, label, 12, True)
                pdf.text(440, y, f'{currency} {amount:.2f}', 13, True)
            pdf.text(42, 370, 'Sample zero-rated transaction for software testing.', 10)
            pdf.text(42, 340, 'Credit limit: USD 5000.00 (not the invoice total)', 10)
        footer(pdf, '2 / 2' if layout == 3 else '1 / 1')
        pdf.save(folder / filename)
        manifest.append(dict(source_file=filename, layout=name, pages=2 if layout == 3 else 1))
    (root / 'invoice_data.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
    (root / 'layouts.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Created {len(records)} varied fictional invoices in {folder}')


if __name__ == '__main__':
    main()
