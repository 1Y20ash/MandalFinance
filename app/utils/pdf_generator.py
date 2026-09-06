import io
from fpdf import FPDF

class ReceiptPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, 'SHREE ASHTAVINAYAK GANESH UTSAV MANDAL', new_x="LMARGIN", new_y="NEXT", align='C')
        self.set_font('Helvetica', '', 10)
        self.cell(0, 5, 'Panchasheel Nagar, Gittikhadan, Nagpur, Maharashtra, India', new_x="LMARGIN", new_y="NEXT", align='C')
        self.cell(0, 5, 'OFFICIAL DONATION RECEIPT', new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln(5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, 'This is a computer-generated receipt. Every rupee accounted for.', align='C')


def generate_donation_receipt_pdf(donation, event_title="Ganesh Utsav 2026"):
    pdf = ReceiptPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', '', 11)

    pdf.cell(100, 8, f"Receipt No: {donation.receipt_number or donation.donation_number}")
    pdf.cell(90, 8, f"Date: {donation.created_at.strftime('%d-%b-%Y')}", new_x="LMARGIN", new_y="NEXT", align='R')
    pdf.cell(100, 8, f"Event: {event_title}")
    pdf.cell(90, 8, f"Payment Mode: {donation.payment_mode}", new_x="LMARGIN", new_y="NEXT", align='R')
    
    pdf.ln(5)
    pdf.cell(0, 8, f"Received with thanks from: {donation.donor_name}", new_x="LMARGIN", new_y="NEXT")
    if donation.donor_phone:
        pdf.cell(0, 8, f"Contact: {donation.donor_phone}", new_x="LMARGIN", new_y="NEXT")
    if donation.pan_number:
        pdf.cell(0, 8, f"PAN: {donation.pan_number}", new_x="LMARGIN", new_y="NEXT")
        
    pdf.cell(0, 8, f"The Sum of: Rs. {donation.amount:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Towards Purpose: {donation.purpose}", new_x="LMARGIN", new_y="NEXT")
    if donation.transaction_ref:
        pdf.cell(0, 8, f"Transaction Ref / UTR: {donation.transaction_ref}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(10)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, f"AMOUNT RECEIVED: Rs. {donation.amount:,.2f}", border=1, new_x="LMARGIN", new_y="NEXT", align='C')

    pdf.ln(15)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(100, 8, "Donor Signature: ______________")
    pdf.cell(90, 8, "Authorized Signatory: ______________", align='R')

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer.getvalue()
