from datetime import date, datetime
from decimal import Decimal

import pytest

from app.extensions import db
from app.models.controls import ReconciliationRecord
from app.models.ledger import Transaction
from app.models.auth import User
from app.services.ledger_service import LedgerService
from app.services.financial_controls_service import FinancialControlsService


def test_reconciliation_handles_expense_reversal_correctly(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        account = __import__('app.models.ledger', fromlist=['Account']).Account.query.filter_by(name='Main Cash').first()
        before = account.current_balance

        expense = LedgerService.record_expense(
            account.id, '200.00', 'Reconciliation expense', 'RECON_TEST', 1, user.id,
            transaction_date=datetime(2026, 9, 8)
        )
        LedgerService.reverse_transaction(expense.id, user.id, 'Incorrect expense')

        record = FinancialControlsService.reconcile_account(
            account.id, date(2026, 9, 8), before, user,
            period_start=date(2026, 9, 8), period_end=date(2026, 9, 8)
        )
        assert record.book_balance == before
        assert record.difference == Decimal('0.00')
        assert record.status == 'MATCHED'


def test_reconciliation_rejects_duplicate_statement_date(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        account = __import__('app.models.ledger', fromlist=['Account']).Account.query.filter_by(name='Main Cash').first()
        statement_date = date(2026, 9, 8)

        FinancialControlsService.reconcile_account(account.id, statement_date, account.current_balance, user)
        with pytest.raises(ValueError, match='already exists'):
            FinancialControlsService.reconcile_account(account.id, statement_date, account.current_balance, user)


def test_reconciliation_routes_require_finance_permission(app):
    client = app.test_client()
    volunteer = User.query.filter_by(username='volunteer').first()
    with client.session_transaction() as session:
        session['_user_id'] = str(volunteer.id)
        session['_fresh'] = True

    with app.app_context():
        account = __import__('app.models.ledger', fromlist=['Account']).Account.query.filter_by(name='Main Cash').first()
        record = ReconciliationRecord(
            reconciliation_ref='REC-AUTH-TEST', account_id=account.id,
            statement_date=date(2026, 9, 8), book_balance=account.current_balance,
            statement_balance=account.current_balance, difference=Decimal('0.00'),
            status='MATCHED', created_by_id=User.query.filter_by(username='admin').first().id
        )
        db.session.add(record)
        db.session.commit()
        record_id = record.id

    response = client.get(f'/finance-controls/reconciliation/{record_id}/lines')
    assert response.status_code == 403


def test_reconciliation_match_prevents_one_transaction_matching_twice(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        account = __import__('app.models.ledger', fromlist=['Account']).Account.query.filter_by(name='Main Cash').first()
        record = FinancialControlsService.reconcile_account(
            account.id, date(2026, 9, 8), account.current_balance, user
        )
        # Import two identical statement lines with distinct references; both should
        # not be allowed to consume the same ledger transaction.
        tx = LedgerService.record_income(
            account.id, '125.00', 'Recon match', 'RECON_MATCH', 1, user.id,
            transaction_date=datetime(2026, 9, 8), external_ref='recon-ext-1'
        )
        # The existing record is still open, so add the first line.
        from app.services.reconciliation_service import ReconciliationService
        lines = ReconciliationService.import_lines(record.id, [{
            'line_ref': 'BANK-1', 'transaction_date': '2026-09-08',
            'amount': '125.00', 'external_ref': 'recon-ext-1'
        }], user)
        ReconciliationService.match_line(lines[0].id, user)
        with pytest.raises(ValueError, match='already matched'):
            # Attempt to create a second statement line for the same transaction.
            lines2 = ReconciliationService.import_lines(record.id, [{
                'line_ref': 'BANK-2', 'transaction_date': '2026-09-08',
                'amount': '125.00', 'external_ref': 'recon-ext-1'
            }], user)
            ReconciliationService.match_line(lines2[0].id, user)
