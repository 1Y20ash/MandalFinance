from decimal import Decimal

from app.extensions import db
from app.models.audit import AuditLog
from app.models.controls import ReconciliationRecord
from app.models.ledger import Account
from app.models.auth import User
from app.services.account_balance_service import AccountBalanceService
from app.services.ledger_service import LedgerService


def test_opening_balance_adjustment_preserves_ledger_reconciliation(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        account = Account.query.filter_by(name='Main Cash').first()
        LedgerService.record_income(account.id, '500.00', 'Opening adjustment test income', 'OPENING_TEST', 1, user.id)
        before_current = account.current_balance

        AccountBalanceService.adjust_opening_balance(account.id, '12000.00', user, 'Correct opening cash count')

        assert account.opening_balance == Decimal('12000.00')
        assert account.current_balance == before_current + Decimal('2000.00')
        reconciliation = next(x for x in LedgerService.get_account_reconciliation() if x['account'].id == account.id)
        assert reconciliation['difference'] == Decimal('0.00')
        assert reconciliation['is_balanced'] is True

        audit = AuditLog.query.filter_by(action='OPENING_BALANCE_ADJUST', entity_type='ACCOUNT', entity_id=str(account.id)).order_by(AuditLog.created_at.desc()).first()
        assert audit is not None
        assert 'Correct opening cash count' in audit.description


def test_opening_balance_adjustment_requires_reason_and_nonnegative_amount(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        account = Account.query.filter_by(name='Main Cash').first()
        original = account.opening_balance

        try:
            AccountBalanceService.adjust_opening_balance(account.id, '12000.00', user, '')
            assert False, 'Expected missing reason to be rejected'
        except ValueError as exc:
            assert 'reason' in str(exc).lower()

        try:
            AccountBalanceService.adjust_opening_balance(account.id, '-1.00', user, 'Invalid correction')
            assert False, 'Expected negative opening balance to be rejected'
        except ValueError as exc:
            assert 'negative' in str(exc).lower()

        assert account.opening_balance == original


def test_opening_balance_cannot_change_after_resolved_reconciliation(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        account = Account.query.filter_by(name='Main Cash').first()
        record = ReconciliationRecord(
            reconciliation_ref='REC-OPENING-LOCK',
            account_id=account.id,
            statement_date=db.func.current_date(),
            book_balance=account.current_balance,
            statement_balance=account.current_balance,
            difference=Decimal('0.00'),
            status='RESOLVED',
            created_by_id=user.id,
            resolved_by_id=user.id,
        )
        db.session.add(record)
        db.session.commit()

        try:
            AccountBalanceService.adjust_opening_balance(account.id, '11000.00', user, 'Should be blocked')
            assert False, 'Expected resolved reconciliation to block opening balance change'
        except ValueError as exc:
            assert 'resolved' in str(exc).lower()


def test_opening_balance_adjustment_route_requires_finance_manage(client):
    response = client.post('/auth/login', data={'username': 'volunteer', 'password': 'password'}, follow_redirects=False)
    assert response.status_code == 302
    response = client.post('/finance-controls/accounts/1/opening-balance', json={'opening_balance': '11000.00', 'reason': 'Unauthorized'})
    assert response.status_code == 403
