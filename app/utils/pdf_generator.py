import io
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.colors import HexColor


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / 'assets' / 'receipt_template.pdf'
TEMPLATE_PAGE_SIZE = (612, 252)
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
    for size in [6.0, 5.75, 5.5, 5.25, 5.0, 4.75, 4.5, 4.25, 4.0]:
        if stringWidth(text, 'Helvetica', size) <= max_width:
            return [(text, size)]

    words = text.split()
    for size in [5.5, 5.25, 5.0, 4.75, 4.5, 4.25, 4.0]:
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

    return [(line, 4.0) for line in lines[:max_lines]]


def _draw_text(c, x, y, text, max_width, max_size, min_size=4.0, bold=False):
    font_name = 'Helvetica-Bold' if bold else 'Helvetica'
    size, text = _fit_text(c, text, font_name, max_size, min_size, max_width)
    c.setFont(font_name, size)
    c.drawString(x, y, text)


def _draw_copy_fields(c, *, receipt_no, date_text, donor_name, amount_words, amount,
                      receipt_x, date_x, donor_x, words_x, words_y, amount_x, amount_y,
                      receipt_width, date_width, donor_width, words_width, amount_width,
                      second_words_x):
    c.setFillColor(TEXT_COLOR)

    _draw_text(c, receipt_x, 164, receipt_no, receipt_width, 6.5, 3.75)
    _draw_text(c, date_x, 164, date_text, date_width, 7.0, 4.5)
    _draw_text(c, donor_x, 133, donor_name, donor_width, 8.0, 4.5)

    word_lines = _wrap_amount_words(amount_words, max_width=words_width, max_lines=2)
    if word_lines:
        c.setFont('Helvetica', word_lines[0][1])
        c.drawString(words_x, words_y, word_lines[0][0])
    if len(word_lines) > 1:
        c.setFont('Helvetica', word_lines[1][1])
        c.drawString(second_words_x, words_y - 20, word_lines[1][0])

    _draw_text(c, amount_x, amount_y, _format_amount(amount), amount_width, 10.0, 6.0, bold=True)


def generate_donation_receipt_pdf(donation, event_title='Ganesh Utsav 2026'):
    """Overlay only recorded donation fields on the original printable receipt template."""
    if not TEMPLATE_PATH.is_file():
        raise FileNotFoundError(f'Receipt template not found: {TEMPLATE_PATH}')

    receipt_no = donation.receipt_number or donation.donation_number or ''
    created_at = donation.receipt_generated_at or donation.created_at
    date_text = created_at.strftime('%d-%m-%Y') if created_at else ''
    donor_name = donation.donor_name or ''
    amount_words = _amount_in_words(donation.amount)

    overlay_buffer = io.BytesIO()
    overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=TEMPLATE_PAGE_SIZE)

    # The source Canva PDF contains two receipt copies on one 612 x 252 pt sheet.
    # Keep the artwork, borders, Marathi labels, lines, and spacing untouched.
    _draw_copy_fields(
        overlay_canvas,
        receipt_no=receipt_no, date_text=date_text, donor_name=donor_name,
        amount_words=amount_words, amount=donation.amount,
        receipt_x=64, date_x=151, donor_x=49, words_x=92, words_y=107,
        amount_x=50, amount_y=53, receipt_width=44, date_width=36, donor_width=132,
        words_width=100, amount_width=112, second_words_x=36,
    )
    _draw_copy_fields(
        overlay_canvas,
        receipt_no=receipt_no, date_text=date_text, donor_name=donor_name,
        amount_words=amount_words, amount=donation.amount,
        receipt_x=265, date_x=347, donor_x=255, words_x=301, words_y=85,
        amount_x=286, amount_y=38, receipt_width=42, date_width=37, donor_width=100,
        words_width=83, amount_width=105, second_words_x=224,
    )

    overlay_canvas.save()
    overlay_buffer.seek(0)

    overlay_reader = PdfReader(overlay_buffer)
    overlay_page = overlay_reader.pages[0]

    # Attach the template page to the writer before merging. This avoids pypdf's
    # replace_contents deprecation warning under the repository's warnings-as-errors CI.
    writer = PdfWriter(clone_from=str(TEMPLATE_PATH))
    template_page = writer.pages[0]
    overlay_page.mediabox = template_page.mediabox
    overlay_page.cropbox = template_page.cropbox
    template_page.merge_page(overlay_page)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
