import io
from decimal import Decimal

from fpdf import FPDF


MANDAL_NAME = 'SHREE ASHTAVINAYAK GANESH UTSAV MANDAL'
MANDAL_ADDRESS = 'Panchasheel Nagar, Gittikhadan, Nagpur, Maharashtra, India'


class ReceiptPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, MANDAL_NAME, new_x='LMARGIN', new_y='NEXT', align='C')
        self.set_font('Helvetica', '', 9)
        self.cell(0, 5, MANDAL_ADDRESS, new_x='LMARGIN', new_y='NEXT', align='C')
        self.set_font('Helvetica', 'B', 11)
        self.cell(0, 7, 'DONATION RECEIPT', new_x='LMARGIN', new_y='NEXT', align='C')
        self.ln(4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-18)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 5, 'Computer-generated receipt | Please retain this receipt for your records.', new_x='LMARGIN', new_y='NEXT', align='C')
        self.cell(0, 5, 'This receipt does not by itself establish any statutory or tax-exemption status.', align='C')


def _safe_text(value):
    """Keep generated PDFs compatible with the built-in Helvetica font."""
    return str(value or '').encode('latin-1', 'replace').decode('latin-1')


def _format_amount(amount):
    return f'Rs. {Decimal(str(amount)):,.2f}'


def generate_donation_receipt_pdf(donation, event_title='Ganesh Utsav 2026'):
    pdf = ReceiptPDF()
    pdf.set_auto_page_break(auto=True, margin=24)
    pdf.add_page()

    receipt_no = donation.receipt_number or donation.donation_number
    created_at = donation.receipt_generated_at or donation.created_at

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(95, 7, _safe_text(f'Receipt No: {receipt_no}'))
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(95, 7, _safe_text(f'Date: {created_at.strftime("%d-%b-%Y %H:%M")}'), new_x='LMARGIN', new_y='NEXT', align='R')
    pdf.cell(95, 7, _safe_text(f'Event: {event_title}'))
    pdf.cell(95, 7, _safe_text(f'Payment Mode: {donation.payment_mode}'), new_x='LMARGIN', new_y='NEXT', align='R')

    pdf.ln(7)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 8, 'DONOR DETAILS', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 7, _safe_text(f'Name: {donation.donor_name}'), new_x='LMARGIN', new_y='NEXT')
    if donation.donor_phone:
        pdf.cell(0, 7, _safe_text(f'Phone: {donation.donor_phone}'), new_x='LMARGIN', new_y='NEXT')
    if donation.donor_email:
        pdf.cell(0, 7, _safe_text(f'Email: {donation.donor_email}'), new_x='LMARGIN', new_y='NEXT')
    if donation.donor_address:
        pdf.multi_cell(0, 7, _safe_text(f'Address: {donation.donor_address}'))

    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 8, 'DONATION DETAILS', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 7, _safe_text(f'Purpose: {donation.purpose}'), new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 7, _safe_text(f'Donation Type: {donation.donation_type}'), new_x='LMARGIN', new_y='NEXT')
    if donation.transaction_ref:
        pdf.cell(0, 7, _safe_text(f'Transaction Ref / UTR: {donation.transaction_ref}'), new_x='LMARGIN', new_y='NEXT')
    if donation.gateway_payment_id:
        pdf.cell(0, 7, _safe_text(f'Gateway Payment ID: {donation.gateway_payment_id}'), new_x='LMARGIN', new_y='NEXT')

    pdf.ln(8)
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 12, _safe_text(f'AMOUNT RECEIVED: {_format_amount(donation.amount)}'), border=1, new_x='LMARGIN', new_y='NEXT', align='C')

    pdf.ln(16)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(95, 7, 'Donor Signature: ____________________')
    pdf.cell(95, 7, 'Authorized Signatory: ____________________', new_x='LMARGIN', new_y='NEXT', align='R')

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer.getvalue()
