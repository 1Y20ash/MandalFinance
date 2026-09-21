import io
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import RectangleObject
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.colors import HexColor


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / 'assets' / 'receipt_template.pdf'

# The supplied Canva source sheet contains two copies. The clean receipt is the
# right-hand copy, which is cropped and used as the single generated receipt.
TEMPLATE_CROP = (206, 0, 612, 252)
TEMPLATE_PAGE_SIZE = (406, 252)
TEXT_COLOR = HexColor('#4A2118')
DEVANAGARI_FONT = Path('/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf')


if DEVANAGARI_FONT.is_file():
    pdfmetrics.registerFont(TTFont('ReceiptDevanagari', str(DEVANAGARI_FONT)))


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


def _fit_text(text, font_name, max_size, min_size, max_width):
    text = str(text or '')
    size = max_size
    while size > min_size and stringWidth(text, font_name, size) > max_width:
        size -= 0.25
    return size, text


def _draw_text(c, x, y, text, max_width, max_size, min_size=4.0, bold=False):
    font_name = 'Helvetica-Bold' if bold else 'Helvetica'
    size, text = _fit_text(text, font_name, max_size, min_size, max_width)
    c.setFont(font_name, size)
    c.drawString(x, y, text)


def _draw_donor_name(c, x, y, donor_name):
    font_name = 'ReceiptDevanagari' if DEVANAGARI_FONT.is_file() else 'Helvetica'
    size, text = _fit_text(donor_name, font_name, 8.0, 4.5, 100)
    c.setFont(font_name, size)
    c.drawString(x, y, text)


def _draw_amount_words(c, text):
    # The amount-in-words field starts on the first printed writing line,
    # immediately after the existing Marathi label. The lower line is part of
    # the artwork and must not be mistaken for the field baseline.
    size, text = _fit_text(text, 'Helvetica', 7.0, 4.0, 76)
    c.setFont('Helvetica', size)
    c.drawString(101.5, 85.8, text)


def _draw_receipt_fields(c, *, receipt_no, date_text, donor_name, amount_words, amount):
    c.setFillColor(TEXT_COLOR)

    # Coordinates are derived from the actual printed baselines/underlines in
    # the supplied right-hand receipt after its 206pt left crop. Keep each
    # value on the corresponding existing line/box rather than introducing
    # a new visual line.
    _draw_text(c, 62, 135.15, receipt_no, 50, 7.0, 3.75)
    _draw_text(c, 141.7, 135.15, date_text, 50, 7.0, 4.5)
    _draw_donor_name(c, 54, 108.6, donor_name)
    _draw_amount_words(c, amount_words)
    _draw_text(c, 80, 38.4, _format_amount(amount), 74, 10.0, 6.0, bold=True)


def generate_donation_receipt_pdf(donation, event_title='Ganesh Utsav 2026'):
    """Generate exactly one receipt using the supplied Canva artwork."""
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

    # Clone the source into a writer before transforming it. This avoids the
    # pypdf deprecation warning that is treated as an error by CI.
    writer = PdfWriter(clone_from=str(TEMPLATE_PATH))
    source_page = writer.pages[0]
    source_page.add_transformation(
        Transformation().translate(tx=-TEMPLATE_CROP[0], ty=-TEMPLATE_CROP[1])
    )
    source_page.mediabox = RectangleObject([0, 0, *TEMPLATE_PAGE_SIZE])
    source_page.cropbox = RectangleObject([0, 0, *TEMPLATE_PAGE_SIZE])
    overlay_page.mediabox = RectangleObject([0, 0, *TEMPLATE_PAGE_SIZE])
    overlay_page.cropbox = RectangleObject([0, 0, *TEMPLATE_PAGE_SIZE])
    source_page.merge_page(overlay_page)

    # The cropped media box exposes only the single clean receipt copy.
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
