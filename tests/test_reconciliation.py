from datetime import date
from decimal import Decimal

import pytest

from app.extensions import db
from app.models.controls import ReconciliationRecord
from app.models.ledger import Account
from app.models.auth import User
from app.services.ledger_service import LedgerService
from app.services.financial_controls_service import FinancialControlsService


def test_reconciliation_handles_expense_reversal_correctly(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        account = Account.query.filter_by(name='Main Cash').first()
        before = account.current_balance

        expense = LedgerService.record_expense(
            account.id, '200.00', 'Reconciliation expense', 'RECON_TEST', 1, user.id
        )
        LedgerService.reverse_transaction(expense.id, user.id, 'Incorrect expense')

        record = FinancialControlsService.reconcile_account(
            account.id, date.today(), before, user,
            period_start=date.today(), period_end=date.today()
        )
        assert record.book_balance == before
        assert record.difference == Decimal('0.00')
        assert record.status == 'MATCHED'


def test_reconciliation_rejects_duplicate_statement_date(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        account = Account.query.filter_by(name='Main Cash').first()
        statement_date = date.today()

        FinancialControlsService.reconcile_account(account.id, statement_date, account.current_balance, user)
        with pytest.raises(ValueError, match='already exists'):
            FinancialControlsService.reconcile_account(account.id, statement_date, account.current_balance, user)


def test_reconciliation_routes_require_finance_permission(client, app):
    # Authenticate through the real login endpoint. Phase 9 enables strong
    # Flask-Login session protection, so hand-written session identifiers are
    # intentionally invalidated when their client identity is not established.
    assert client.post(
        '/auth/login',
        data={'username': 'volunteer', 'password': 'password'},
        follow_redirects=False,
    ).status_code == 302

    with app.app_context():
        account = Account.query.filter_by(name='Main Cash').first()
        admin = User.query.filter_by(username='admin').first()
        record = ReconciliationRecord(
            reconciliation_ref='REC-AUTH-TEST', account_id=account.id,
            statement_date=date.today(), book_balance=account.current_balance,
            statement_balance=account.current_balance, difference=Decimal('0.00'),
            status='MATCHED', created_by_id=admin.id
        )
        db.session.add(record)
        db.session.commit()
        record_id = record.id

    response = client.get(f'/finance-controls/reconciliation/{record_id}/lines')
    assert response.status_code == 403


def test_reconciliation_match_prevents_one_transaction_matching_twice(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        account = Account.query.filter_by(name='Main Cash').first()
        record = FinancialControlsService.reconcile_account(
            account.id, date.today(), account.current_balance, user
        )

        tx = LedgerService.record_income(
            account.id, '125.00', 'Recon match', 'RECON_MATCH', 1, user.id,
            external_ref='recon-ext-1'
        )

        from app.services.reconciliation_service import ReconciliationService
        lines = ReconciliationService.import_lines(record.id, [{
            'line_ref': 'BANK-1', 'transaction_date': date.today().isoformat(),
            'amount': '125.00', 'external_ref': 'recon-ext-1'
        }], user)
        ReconciliationService.match_line(lines[0].id, user)

        lines2 = ReconciliationService.import_lines(record.id, [{
            'line_ref': 'BANK-2', 'transaction_date': date.today().isoformat(),
            'amount': '125.00', 'external_ref': 'recon-ext-1'
        }], user)
        with pytest.raises(ValueError, match='already matched'):
            ReconciliationService.match_line(lines2[0].id, user)

        assert tx.id == lines[0].matched_transaction_id
