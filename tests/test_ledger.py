from decimal import Decimal
import pytest
from app.models.ledger import Account
from app.models.auth import User
from app.services.ledger_service import LedgerService

def test_ledger_income_and_expense_precision(app):
    with app.app_context():
        account = Account.query.filter_by(name='Main Cash').first()
        user = User.query.filter_by(username='admin').first()

        initial_bal = account.current_balance
        assert isinstance(initial_bal, Decimal)

        # Record Income
        txn_inc = LedgerService.record_income(
            account_id=account.id,
            amount='1500.50',
            description='Test Income',
            source_module='DONATION',
            source_id=1,
            created_by_id=user.id
        )

        assert account.current_balance == initial_bal + Decimal('1500.50')
        assert txn_inc.amount == Decimal('1500.50')

        # Record Expense
        txn_exp = LedgerService.record_expense(
            account_id=account.id,
            amount='500.25',
            description='Test Expense',
            source_module='EXPENSE',
            source_id=1,
            created_by_id=user.id
        )

        assert account.current_balance == initial_bal + Decimal('1500.50') - Decimal('500.25')

        # Reversal
        rev_txn = LedgerService.reverse_transaction(txn_exp.id, user.id, 'Duplicate entry error')
        assert txn_exp.is_reversed is True
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
