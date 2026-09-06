from decimal import Decimal

import pytest

from app.extensions import db
from app.models.audit import AuditLog
from app.models.income import Donation
from app.models.ledger import Account, Transaction
from app.models.auth import User
from app.services.donation_service import DonationService


def _ids():
    event_id = db.session.execute(db.select(DonationService.__dict__.get('_missing', Donation))).scalar() if False else None
    from app.models.mandal import Event
    return Event.query.first().id, Account.query.filter_by(name='Main Cash').first(), User.query.filter_by(username='admin').first()


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
        txn = Transaction.query.filter_by(source_module='DONATION', source_id=saved.id).one()
        assert txn.amount == Decimal('1250.50')
        assert txn.transaction_type == 'INCOME'
        assert db.session.get(Account, account.id).current_balance == before + Decimal('1250.50')
        assert AuditLog.query.filter_by(entity_type='DONATION', entity_id=str(saved.id)).count() == 1


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
