import io
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.colors import HexColor


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / 'assets' / 'receipt_template.pdf'

# The Canva source sheet contains two copies. The supplied design is the
# single receipt on the right-hand side of that source sheet.
TEMPLATE_CROP = (206, 0, 612, 252)
TEMPLATE_PAGE_SIZE = (406, 252)
TEXT_COLOR = HexColor('#4A2118')


def _format_amount(amount):
    return f'{Decimal(str(amount)):,.2f}'


def _amount_in_words(amount):
    value = Decimal(str(amount)).quantize(Decimal('0.01'))
    rupees = int(value)
    paise = int((value - rupees) * 100)

    ones = [
        'Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
        'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen',
        'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen',
    ]
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


def _fit_text(c, text, font_name, max_size, min_size, max_width):
    text = str(text or '')
    size = max_size
    while size > min_size and stringWidth(text, font_name, size) > max_width:
        size -= 0.25
    return size, text


def _wrap_amount_words(text, max_width, max_lines=2):
    text = str(text or '').strip()
    for size in [8.0, 7.75, 7.5, 7.25, 7.0, 6.75, 6.5, 6.25, 6.0, 5.75, 5.5]:
        if stringWidth(text, 'Helvetica', size) <= max_width:
            return [(text, size)]

    words = text.split()
    for size in [7.0, 6.75, 6.5, 6.25, 6.0, 5.75, 5.5]:
        lines = []
        current = ''
        for word in words:
            candidate = word if not current else f'{current} {word}'
            if stringWidth(candidate, 'Helvetica', size) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        if len(lines) <= max_lines:
            return [(line, size) for line in lines]

    return [(line, 5.5) for line in lines[:max_lines]]


def _draw_text(c, x, y, text, max_width, max_size, min_size=4.0, bold=False):
    font_name = 'Helvetica-Bold' if bold else 'Helvetica'
    size, text = _fit_text(c, text, font_name, max_size, min_size, max_width)
    c.setFont(font_name, size)
    c.drawString(x, y, text)


def _draw_receipt_fields(c, *, receipt_no, date_text, donor_name, amount_words, amount):
    c.setFillColor(TEXT_COLOR)

    # Coordinates are for the single cropped receipt, in points.
    _draw_text(c, 59, 164, receipt_no, 44, 7.0, 3.75)
    _draw_text(c, 141, 164, date_text, 37, 7.0, 4.5)
    _draw_text(c, 49, 133, donor_name, 100, 8.0, 4.5)

    word_lines = _wrap_amount_words(amount_words, max_width=83, max_lines=2)
    c.setFont('Helvetica', word_lines[0][1])
    c.drawString(95, 85, word_lines[0][0])
    if len(word_lines) > 1:
        c.setFont('Helvetica', word_lines[1][1])
        c.drawString(18, 65, word_lines[1][0])

    _draw_text(c, 80, 38, _format_amount(amount), 105, 10.0, 6.0, bold=True)


def generate_donation_receipt_pdf(donation, event_title='Ganesh Utsav 2026'):
    """Generate one receipt using the supplied Canva artwork as the fixed template."""
    if not TEMPLATE_PATH.is_file():
        raise FileNotFoundError(f'Receipt template not found: {TEMPLATE_PATH}')

    receipt_no = donation.receipt_number or donation.donation_number or ''
    created_at = donation.receipt_generated_at or donation.created_at
    date_text = created_at.strftime('%d-%m-%Y') if created_at else ''
    donor_name = donation.donor_name or ''
    amount_words = _amount_in_words(donation.amount)

    overlay_buffer = io.BytesIO()
    overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=TEMPLATE_PAGE_SIZE)
    _draw_receipt_fields(
        overlay_canvas,
        receipt_no=receipt_no,
        date_text=date_text,
        donor_name=donor_name,
        amount_words=amount_words,
        amount=donation.amount,
    )
    overlay_canvas.save()
    overlay_buffer.seek(0)

    overlay_page = PdfReader(overlay_buffer).pages[0]

    # Crop the single receipt from the original Canva source sheet and translate
    # its artwork to the origin. This keeps the artwork itself untouched.
    source_page = PdfReader(str(TEMPLATE_PATH)).pages[0]
    source_page.mediabox.lower_left = (TEMPLATE_CROP[0], TEMPLATE_CROP[1])
    source_page.mediabox.upper_right = (TEMPLATE_CROP[2], TEMPLATE_CROP[3])
    source_page.cropbox.lower_left = (TEMPLATE_CROP[0], TEMPLATE_CROP[1])
    source_page.cropbox.upper_right = (TEMPLATE_CROP[2], TEMPLATE_CROP[3])
    source_page.add_transformation(Transformation().translate(
        tx=-TEMPLATE_CROP[0],
        ty=-TEMPLATE_CROP[1],
    ))

    overlay_page.mediabox = source_page.mediabox
    overlay_page.cropbox = source_page.cropbox
    source_page.merge_page(overlay_page)

    writer = PdfWriter()
    writer.add_page(source_page)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
