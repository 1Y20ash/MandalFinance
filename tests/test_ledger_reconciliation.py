from decimal import Decimal

import pytest

from app.extensions import db
from app.models.ledger import Account
from app.models.auth import User
from app.services.ledger_service import LedgerService


def test_account_reconciliation_matches_posted_ledger(app):
    with app.app_context():
        account = Account.query.filter_by(name='Main Cash').first()
        user = User.query.filter_by(username='admin').first()

        LedgerService.record_income(
            account.id, '1250.75', 'Reconciliation income', 'RECON_TEST', 1, user.id
        )
        LedgerService.record_expense(
            account.id, '250.25', 'Reconciliation expense', 'RECON_TEST', 2, user.id
        )

        row = next(r for r in LedgerService.get_account_reconciliation() if r['account'].id == account.id)
        assert row['opening_balance'] == Decimal('10000.00')
        assert row['income'] == Decimal('1250.75')
        assert row['expense'] == Decimal('250.25')
        assert row['expected_balance'] == Decimal('11000.50')
        assert row['stored_balance'] == Decimal('11000.50')
        assert row['difference'] == Decimal('0.00')
        assert row['is_balanced'] is True


def test_reconciliation_detects_balance_drift(app):
    with app.app_context():
        account = Account.query.filter_by(name='Main Cash').first()
        account.current_balance += Decimal('0.01')
        db.session.commit()

        row = next(r for r in LedgerService.get_account_reconciliation() if r['account'].id == account.id)
        assert row['difference'] == Decimal('0.01')
        assert row['is_balanced'] is False


def test_recent_transactions_limit_is_bounded(app):
    with app.app_context():
        assert len(LedgerService.get_recent_transactions(limit=1)) <= 1
        with pytest.raises((TypeError, ValueError)):
            LedgerService.get_recent_transactions(limit='not-a-number')
        assert len(LedgerService.get_recent_transactions(limit=999999)) <= 500
