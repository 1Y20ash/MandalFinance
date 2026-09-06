from decimal import Decimal

import pytest

from app.extensions import db
from app.models.audit import AuditLog
from app.models.ledger import Account, Transaction
from app.models.auth import User
from app.services.audit_service import AuditService
from app.services.ledger_service import LedgerService


def test_ledger_income_and_expense_precision(app):
    with app.app_context():
        account = Account.query.filter_by(name='Main Cash').first()
        user = User.query.filter_by(username='admin').first()
        initial_bal = account.current_balance
        assert isinstance(initial_bal, Decimal)

        txn_inc = LedgerService.record_income(
            account_id=account.id, amount='1500.50', description='Test Income',
            source_module='DONATION', source_id=1, created_by_id=user.id
        )
        assert account.current_balance == initial_bal + Decimal('1500.50')
        assert txn_inc.amount == Decimal('1500.50')

        txn_exp = LedgerService.record_expense(
            account_id=account.id, amount='500.25', description='Test Expense',
            source_module='EXPENSE', source_id=1, created_by_id=user.id
        )
        assert account.current_balance == initial_bal + Decimal('1500.50') - Decimal('500.25')

        rev_txn = LedgerService.reverse_transaction(txn_exp.id, user.id, 'Duplicate entry error')
        assert txn_exp.is_reversed is True
        assert txn_exp.reversed_by_txn_id == rev_txn.id
        assert account.current_balance == initial_bal + Decimal('1500.50')


def test_ledger_summary_calculation(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        account = Account.query.filter_by(name='Main Cash').first()

        LedgerService.record_income(account.id, '2000.00', 'Inc', 'TEST', 1, user.id)
        LedgerService.record_expense(account.id, '500.00', 'Exp', 'TEST', 2, user.id)

        summary = LedgerService.get_ledger_summary()
        assert summary['opening_balance'] == Decimal('10000.00')
        assert summary['total_income'] == Decimal('2000.00')
        assert summary['total_expense'] == Decimal('500.00')
        assert summary['current_balance'] == Decimal('11500.00')


def test_duplicate_source_is_rejected_without_balance_change(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        account = Account.query.filter_by(name='Main Cash').first()
        before = account.current_balance

        LedgerService.record_income(account.id, '100.00', 'First', 'TEST_DUP', 999, user.id)
        after_first = account.current_balance

        with pytest.raises(ValueError, match='already exists'):
            LedgerService.record_income(account.id, '100.00', 'Duplicate', 'TEST_DUP', 999, user.id)

        db_account = db.session.get(Account, account.id)
        assert db_account.current_balance == after_first
        assert db_account.current_balance == before + Decimal('100.00')


def test_duplicate_external_ref_is_rejected(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        account = Account.query.filter_by(name='Main Cash').first()
        LedgerService.record_income(
            account.id, '75.00', 'Gateway payment', 'PAYMENT', 1, user.id,
            external_ref='gateway-unique-1'
        )

        with pytest.raises(ValueError, match='external reference'):
            LedgerService.record_income(
                account.id, '75.00', 'Duplicate gateway payment', 'PAYMENT', 2, user.id,
                external_ref='gateway-unique-1'
            )


def test_reversal_requires_reason_and_cannot_reverse_reversal(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        account = Account.query.filter_by(name='Main Cash').first()
        txn = LedgerService.record_income(account.id, '50.00', 'Reversible', 'REV_TEST', 1, user.id)

        with pytest.raises(ValueError, match='reason is required'):
            LedgerService.reverse_transaction(txn.id, user.id, '   ')

        reversal = LedgerService.reverse_transaction(txn.id, user.id, 'Correction')
        with pytest.raises(ValueError, match='already been reversed'):
            LedgerService.reverse_transaction(txn.id, user.id, 'Again')
        with pytest.raises(ValueError, match='Only INCOME and EXPENSE'):
            LedgerService.reverse_transaction(reversal.id, user.id, 'Invalid reversal')


def test_ledger_rolls_back_when_audit_logging_fails(app, monkeypatch):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        account = Account.query.filter_by(name='Main Cash').first()
        before = account.current_balance

        def failing_audit(*args, **kwargs):
            raise RuntimeError('simulated audit failure')

        monkeypatch.setattr(AuditService, 'log_action', failing_audit)

        with pytest.raises(RuntimeError, match='simulated audit failure'):
            LedgerService.record_income(
                account.id, '125.00', 'Atomicity test', 'ATOMICITY_TEST', 1, user.id
            )

        db.session.expire_all()
        db_account = db.session.get(Account, account.id)
        assert db_account.current_balance == before
        assert Transaction.query.filter_by(source_module='ATOMICITY_TEST', source_id=1).first() is None
        assert AuditLog.query.filter_by(entity_type='TRANSACTION', description='Recorded INCOME of ₹125.00 to account \'Main Cash\'').first() is None
