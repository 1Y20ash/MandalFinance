from decimal import Decimal

import pytest

from app.extensions import db
from app.models.contribution import MemberContributionPayment, SponsorshipPayment
from app.models.income import MemberContribution, Sponsorship
from app.models.ledger import Account, Transaction
from app.models.auth import User
from app.services.contribution_service import ContributionService


def _context():
    user = User.query.filter_by(username='admin').first()
    event = next((e for e in __import__('app.models.mandal', fromlist=['Event']).Event.query.filter_by(is_active=True).all()), None)
    account = Account.query.filter_by(name='Main Cash').first()
    assert user and event and account
    return user, event, account


def test_sponsorship_payment_posts_to_ledger_and_updates_balance(app):
    with app.app_context():
        user, event, account = _context()
        sponsorship = ContributionService.create_sponsorship(event.id, 'Test Sponsor', 'Gold Package', '1000.00', user.id)
        before = account.current_balance
        payment = ContributionService.record_sponsorship_payment(sponsorship.id, account.id, '400.00', 'CASH', 'SP-TEST-001', user.id)

        db.session.expire_all()
        stored = db.session.get(Sponsorship, sponsorship.id)
        ledger = db.session.get(Transaction, payment.ledger_transaction_id)
        assert stored.committed_amount == Decimal('1000.00')
        assert stored.received_amount == Decimal('400.00')
        assert stored.pending_amount == Decimal('600.00')
        assert stored.status == 'PARTIAL'
        assert ledger.source_module == 'SPONSORSHIP_PAYMENT'
        assert ledger.source_id == payment.id
        assert account.current_balance == before + Decimal('400.00')


def test_member_payment_cannot_exceed_target_or_duplicate_reference(app):
    with app.app_context():
        user, event, account = _context()
        contribution = ContributionService.create_member_contribution(event.id, 'Test Member', '500.00', user.id)

        with pytest.raises(ValueError, match='exceed'):
            ContributionService.record_member_payment(contribution.id, account.id, '500.01', 'UPI', 'MC-OVER', user.id)

        ContributionService.record_member_payment(contribution.id, account.id, '200.00', 'UPI', 'MC-001', user.id)
        with pytest.raises(ValueError, match='already been used'):
            ContributionService.record_member_payment(contribution.id, account.id, '100.00', 'UPI', 'MC-001', user.id)

        stored = db.session.get(MemberContribution, contribution.id)
        assert stored.received_amount == Decimal('200.00')
        assert stored.pending_amount == Decimal('300.00')
        assert stored.status == 'PARTIAL'


def test_contribution_payment_rolls_back_if_ledger_posting_fails(app, monkeypatch):
    with app.app_context():
        user, event, account = _context()
        sponsorship = ContributionService.create_sponsorship(event.id, 'Atomic Sponsor', 'Silver', '750.00', user.id)
        before = account.current_balance

        def fail(*args, **kwargs):
            raise RuntimeError('ledger failure')

        monkeypatch.setattr('app.services.contribution_service.LedgerService.record_income', fail)
        with pytest.raises(RuntimeError, match='ledger failure'):
            ContributionService.record_sponsorship_payment(sponsorship.id, account.id, '100.00', 'CASH', 'ATOMIC-SP-1', user.id)

        db.session.expire_all()
        stored = db.session.get(Sponsorship, sponsorship.id)
        assert stored.received_amount == Decimal('0.00')
        assert stored.pending_amount == Decimal('750.00')
        assert SponsorshipPayment.query.filter_by(transaction_ref='ATOMIC-SP-1').first() is None
        assert account.current_balance == before


def test_contribution_payment_rejected_for_locked_event(app):
    with app.app_context():
        user, event, account = _context()
        sponsorship = ContributionService.create_sponsorship(event.id, 'Locked Sponsor', 'Bronze', '250.00', user.id)
        event.status = 'LOCKED'
        db.session.commit()
        with pytest.raises(ValueError, match='locked'):
            ContributionService.record_sponsorship_payment(sponsorship.id, account.id, '50.00', 'CASH', 'LOCKED-SP-1', user.id)
