import io
from decimal import Decimal
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.extensions import db
from app.models.audit import AuditLog
from app.models.auth import User
from app.models.income import Donation
from app.models.ledger import Account, Transaction
from app.models.mandal import Event
from app.services.donation_service import DonationService
from app.utils.pdf_generator import generate_donation_receipt_pdf


def _ids():
    return (
        Event.query.first().id,
        Account.query.filter_by(name='Main Cash').first(),
        User.query.filter_by(username='admin').first(),
    )


def test_offline_donation_posts_once_to_ledger_and_audit(app):
    with app.app_context():
        event_id, account, user = _ids()
        before = account.current_balance
        donation = DonationService.record_offline_donation(
            event_id=event_id, donor_name='Test Donor', amount='1250.50', payment_mode='CASH',
            account_id=account.id, created_by_id=user.id, purpose='General Donation'
        )
        db.session.expire_all()
        saved = db.session.get(Donation, donation.id)
        assert saved.status == 'SUCCESS'
        assert saved.amount == Decimal('1250.50')
        assert saved.receipt_number
        assert saved.receipt_generated_at is not None
        txn = Transaction.query.filter_by(source_module='DONATION', source_id=saved.id).one()
        assert txn.amount == Decimal('1250.50')
        assert txn.transaction_type == 'INCOME'
        assert db.session.get(Account, account.id).current_balance == before + Decimal('1250.50')
        assert AuditLog.query.filter_by(entity_type='DONATION', entity_id=str(saved.id)).count() == 1


def test_recorded_donation_generates_original_template_receipt(app):
    with app.app_context():
        event_id, account, user = _ids()
        donation = DonationService.record_offline_donation(
            event_id=event_id, donor_name='Receipt Test', amount='1500.00', payment_mode='CASH',
            account_id=account.id, created_by_id=user.id, purpose='General Donation'
        )
        pdf = generate_donation_receipt_pdf(donation)
        assert pdf.startswith(b'%PDF-')

        reader = PdfReader(io.BytesIO(pdf))
        assert len(reader.pages) == 1
        page = reader.pages[0]
        assert float(page.mediabox.width) == pytest.approx(612)
        assert float(page.mediabox.height) == pytest.approx(252)

        text = page.extract_text() or ''
        assert text.count('Receipt Test') == 2
        assert text.count('1,500.00') == 2
        assert text.count(donation.receipt_generated_at.strftime('%d-%m-%Y')) == 2


def test_receipt_template_is_tracked_and_is_not_replaced_by_code():
    template = Path(__file__).resolve().parents[1] / 'app' / 'assets' / 'receipt_template.pdf'
    assert template.is_file()
    reader = PdfReader(str(template))
    assert len(reader.pages) == 1
    assert float(reader.pages[0].mediabox.width) == pytest.approx(612)
    assert float(reader.pages[0].mediabox.height) == pytest.approx(252)


def test_cash_donation_treats_blank_transaction_reference_as_null(app):
    with app.app_context():
        event_id, account, user = _ids()
        donation = DonationService.record_offline_donation(
            event_id=event_id, donor_name='Blank Ref Cash Donor', amount='250.00', payment_mode='CASH',
            account_id=account.id, created_by_id=user.id, transaction_ref=''
        )
        db.session.expire_all()
        saved = db.session.get(Donation, donation.id)
        txn = Transaction.query.filter_by(source_module='DONATION', source_id=saved.id).one()
        assert saved.transaction_ref is None
        assert txn.external_ref is None


def test_non_cash_donation_requires_reference(app):
    with app.app_context():
        event_id, account, user = _ids()
        with pytest.raises(ValueError, match='Transaction reference'):
            DonationService.record_offline_donation(
                event_id=event_id, donor_name='Test Donor', amount='100.00', payment_mode='UPI',
                account_id=account.id, created_by_id=user.id
            )


def test_invalid_donation_amount_is_rejected(app):
    with app.app_context():
        event_id, account, user = _ids()
        with pytest.raises(ValueError, match='greater than zero'):
            DonationService.record_offline_donation(
                event_id=event_id, donor_name='Test Donor', amount='0', payment_mode='CASH',
                account_id=account.id, created_by_id=user.id
            )


def test_donation_rolls_back_if_ledger_posting_fails(app, monkeypatch):
    with app.app_context():
        event_id, account, user = _ids()
        before = account.current_balance

        def fail_posting(*args, **kwargs):
            raise RuntimeError('simulated ledger failure')

        monkeypatch.setattr('app.services.donation_service.LedgerService.record_income', fail_posting)
        with pytest.raises(RuntimeError, match='simulated ledger failure'):
            DonationService.record_offline_donation(
                event_id=event_id, donor_name='Rollback Donor', amount='500.00', payment_mode='CASH',
                account_id=account.id, created_by_id=user.id
            )

        db.session.expire_all()
        assert db.session.get(Account, account.id).current_balance == before
        assert Donation.query.filter_by(donor_name='Rollback Donor').first() is None


def test_save_donation_redirects_to_intermediate_options_page(app, client):
    with app.app_context():
        event = Event.query.first()
        account = Account.query.filter_by(name='Main Cash').first()
        user = User.query.filter_by(username='admin').first()

        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True

        response = client.post('/donations/create', data={
            'event_id': event.id,
            'account_id': account.id,
            'donor_name': 'Intermediate Options Donor',
            'amount': '500.00',
            'payment_mode': 'CASH',
            'transaction_ref': '',
            'donor_phone': '',
            'donor_email': '',
            'donor_address': '',
            'pan_number': '',
            'purpose': 'General Donation',
            'notes': '',
        }, follow_redirects=False)

        assert response.status_code == 302
        assert response.headers['Location'].endswith(
            f'/donations/{Donation.query.filter_by(donor_name="Intermediate Options Donor").one().id}'
        )
        assert not response.headers['Content-Type'].startswith('application/pdf')
