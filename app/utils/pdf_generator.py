import io
from decimal import Decimal

from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas


PAGE_WIDTH = 407
PAGE_HEIGHT = 252
MANDAL_NAME = 'SHREE ASHTAVINAYAK GANESH UTSAV MANDAL'
MANDAL_ADDRESS = 'Panchasheel Nagar, Katol Road, Gittikhadan, Nagpur, Maharashtra'
BROWN = HexColor('#5B2B1A')
GOLD = HexColor('#C99A2E')


def _safe_text(value, fallback=''):
    return str(value if value is not None else fallback).encode('latin-1', 'replace').decode('latin-1')


def _format_amount(amount):
    return f'{Decimal(str(amount)):,.2f}'


def _amount_in_words(amount):
    value = Decimal(str(amount)).quantize(Decimal('0.01'))
    rupees = int(value)
    paise = int((value - rupees) * 100)
    ones = ['Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

    def under_thousand(number):
        parts = []
        if number >= 100:
            parts.extend([ones[number // 100], 'Hundred'])
            number %= 100
        if number >= 20:
            parts.append(tens[number // 10])
            number %= 10
        if number:
            parts.append(ones[number])
        return ' '.join(parts) or 'Zero'

    def indian_words(number):
        if number == 0:
            return 'Zero'
        parts = []
        crore, number = divmod(number, 10_000_000)
        lakh, number = divmod(number, 100_000)
        thousand, number = divmod(number, 1_000)
        if crore:
            parts.extend([under_thousand(crore), 'Crore'])
        if lakh:
            parts.extend([under_thousand(lakh), 'Lakh'])
        if thousand:
            parts.extend([under_thousand(thousand), 'Thousand'])
        if number:
            parts.append(under_thousand(number))
        return ' '.join(parts)

    result = f'{indian_words(rupees)} Rupees'
    if paise:
        result += f' and {under_thousand(paise)} Paise'
    return result + ' Only'


def _draw_corner(c, x, y, sx, sy):
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.circle(x + sx * 6, y + sy * 6, 10, stroke=1, fill=0)
    c.line(x, y, x + sx * 18, y)
    c.line(x, y, x, y + sy * 18)
    c.circle(x + sx * 12, y + sy * 12, 3, stroke=1, fill=0)


def _draw_ganesh_motif(c, cx=315, cy=128):
    c.saveState()
    c.setStrokeColor(GOLD)
    c.setFillColor(HexColor('#F7D4D7'))
    c.setLineWidth(1)
    c.circle(cx, cy, 39, stroke=1, fill=1)
    c.circle(cx, cy + 12, 21, stroke=1, fill=1)
    c.ellipse(cx - 29, cy + 1, cx - 7, cy + 34, stroke=1, fill=1)
    c.ellipse(cx + 7, cy + 1, cx + 29, cy + 34, stroke=1, fill=1)
    c.setFillColor(HexColor('#E7A0A8'))
    c.circle(cx, cy + 17, 14, stroke=0, fill=1)
    c.setStrokeColor(BROWN)
    c.setFillColor(BROWN)
    c.circle(cx - 7, cy + 19, 1.7, stroke=1, fill=1)
    c.circle(cx + 7, cy + 19, 1.7, stroke=1, fill=1)
    c.setLineWidth(3)
    c.bezier(cx, cy + 11, cx + 9, cy + 2, cx + 12, cy - 8, cx + 2, cy - 17)
    c.setLineWidth(1)
    c.line(cx - 6, cy + 7, cx, cy + 2)
    c.line(cx + 6, cy + 7, cx, cy + 2)
    c.restoreState()


def _draw_receipt_background(c):
    c.setFillColor(HexColor('#FFFDF8'))
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1)
    c.rect(4, 4, PAGE_WIDTH - 8, PAGE_HEIGHT - 8, stroke=1, fill=0)
    for args in ((8, 8, 1, 1), (PAGE_WIDTH - 8, 8, -1, 1), (8, PAGE_HEIGHT - 8, 1, -1), (PAGE_WIDTH - 8, PAGE_HEIGHT - 8, -1, -1)):
        _draw_corner(c, *args)

    c.setFillColor(BROWN)
    c.setFont('Helvetica-Bold', 13)
    c.drawCentredString(PAGE_WIDTH / 2, 234, MANDAL_NAME)
    c.setFont('Helvetica-Bold', 10)
    c.drawCentredString(PAGE_WIDTH / 2, 216, 'DONATION RECEIPT')
    c.setFont('Helvetica', 6.5)
    c.drawCentredString(PAGE_WIDTH / 2, 207, MANDAL_ADDRESS)
    c.setStrokeColor(GOLD)
    c.line(135, 202, 272, 202)

    c.setStrokeColor(GOLD)
    c.line(205, 52, 205, 195)
    c.circle(205, 126, 10, stroke=1, fill=0)
    c.setFillColor(GOLD)
    c.setFont('Helvetica-Bold', 8)
    c.drawCentredString(205, 123, 'OM')
    _draw_ganesh_motif(c)

    c.setFillColor(BROWN)
    c.setFont('Helvetica-Bold', 7)
    c.drawCentredString(PAGE_WIDTH / 2, 15, 'GANPATI BAPPA MORYA • MANGAL MURTI MORYA')


def generate_donation_receipt_pdf(donation, event_title='Ganesh Utsav 2026'):
    """Generate the compact physical receipt after a successful donation recording."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    _draw_receipt_background(c)

    receipt_no = donation.receipt_number or donation.donation_number
    created_at = donation.receipt_generated_at or donation.created_at
    date_text = created_at.strftime('%d-%m-%Y') if created_at else ''

    c.setFillColor(BROWN)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(20, 179, 'Receipt No.')
    c.setFont('Helvetica', 6.3)
    c.drawString(64, 179, _safe_text(receipt_no))
    c.setFont('Helvetica-Bold', 9)
    c.drawString(177, 179, 'Date:')
    c.setFont('Helvetica', 7)
    c.drawString(207, 179, _safe_text(date_text))

    c.setFont('Helvetica-Bold', 9)
    c.drawString(20, 151, 'Donor Name')
    c.setFont('Helvetica', 8)
    c.drawString(91, 151, _safe_text(donation.donor_name))
    c.line(20, 146, 185, 146)

    c.setFont('Helvetica-Bold', 8.5)
    c.drawString(20, 126, 'Amount in words')
    c.setFont('Helvetica', 5.4)
    words = _amount_in_words(donation.amount)
    max_width = 92
    if c.stringWidth(words, 'Helvetica', 5.4) > max_width:
        words = f'{_format_amount(donation.amount)} Rupees Only'
    c.drawString(104, 126, _safe_text(words))
    c.line(20, 121, 185, 121)

    c.setStrokeColor(HexColor('#666666'))
    c.roundRect(55, 35, 112, 28, 6, stroke=1, fill=0)
    c.setFillColor(BROWN)
    c.setFont('Helvetica-Bold', 10.5)
    c.drawString(65, 45, _safe_text(_format_amount(donation.amount)))

    c.save()
    buffer.seek(0)
    return buffer.getvalue()
