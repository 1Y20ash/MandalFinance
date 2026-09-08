from decimal import Decimal

from app.extensions import db
from app.models.income import Donation
from app.models.mandal import Event
from app.models.ledger import Account
from app.models.auth import User
from app.services.donation_service import DonationService
from app.utils.pdf_generator import generate_donation_receipt_pdf


def test_successful_offline_donation_has_stable_receipt_metadata(app):
    with app.app_context():
        event = Event.query.first()
        account = Account.query.filter_by(name='Main Cash').first()
        user = User.query.filter_by(username='admin').first()

        donation = DonationService.record_offline_donation(
            event_id=event.id,
            donor_name='Receipt Test Donor',
            amount='750.00',
            payment_mode='CASH',
            account_id=account.id,
            created_by_id=user.id,
        )

        receipt_number = donation.receipt_number
        generated_at = donation.receipt_generated_at
        assert receipt_number.startswith('REC-')
        assert generated_at is not None

        db.session.expire_all()
        saved = db.session.get(Donation, donation.id)
        assert saved.receipt_number == receipt_number
        assert saved.receipt_generated_at == generated_at


def test_receipt_pdf_is_generated_for_successful_donation(app):
    with app.app_context():
        event = Event.query.first()
        account = Account.query.filter_by(name='Main Cash').first()
        user = User.query.filter_by(username='admin').first()

        donation = DonationService.record_offline_donation(
            event_id=event.id,
            donor_name='PDF Test Donor',
            amount=Decimal('1250.50'),
            payment_mode='CASH',
            account_id=account.id,
            created_by_id=user.id,
            purpose='Festival Donation',
        )

        pdf_bytes = generate_donation_receipt_pdf(donation, event_title=event.title)
        assert pdf_bytes.startswith(b'%PDF-')
        assert b'%%EOF' in pdf_bytes
        assert len(pdf_bytes) > 1000
