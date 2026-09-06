from datetime import date
from decimal import Decimal

import pytest

from app.extensions import db
from app.models.auth import User
from app.models.income_entry import Income
from app.models.ledger import Transaction, TransactionCategory
from app.services.income_service import IncomeService


def _admin(app):
    with app.app_context():
        return User.query.filter_by(username='admin').first()


def _ids(app):
    with app.app_context():
        event = db.session.execute(db.select(__import__('app.models.mandal', fromlist=['Event']).Event)).scalars().first()
        account = db.session.execute(db.select(__import__('app.models.ledger', fromlist=['Account']).Account)).scalars().first()
        category = TransactionCategory.query.filter_by(name='Donations', category_type='income').first()
        return event.id, account.id, category.id


def test_income_posts_once_to_central_ledger(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        event_id, account_id, category_id = _ids(app)
        income = IncomeService.record_income(event_id, category_id, account_id, 'Stall Rental',
                                             'Rental received for festival stall', '1250.50', date.today(),
                                             'UPI', user.id, transaction_ref='UPI-INCOME-001')
        assert income.income_ref.startswith('INC-')
        assert income.transaction_id is not None
        txn = db.session.get(Transaction, income.transaction_id)
        assert txn.transaction_type == 'INCOME'
        assert txn.amount == Decimal('1250.50')
        assert txn.source_module == 'INCOME'
        assert txn.source_id == income.id
        account = db.session.get(__import__('app.models.ledger', fromlist=['Account']).Account, account_id)
        assert account.current_balance == Decimal('11250.50')


def test_non_cash_income_requires_transaction_reference(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        event_id, account_id, category_id = _ids(app)
        with pytest.raises(ValueError, match='Transaction reference'):
            IncomeService.record_income(event_id, category_id, account_id, 'Interest', 'Bank interest',
                                        '100', date.today(), 'BANK_TRANSFER', user.id)


def test_invalid_income_amount_rejected(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        event_id, account_id, category_id = _ids(app)
        with pytest.raises(ValueError, match='greater than zero'):
            IncomeService.record_income(event_id, category_id, account_id, 'Refund', 'Refund received',
                                        '0', date.today(), 'CASH', user.id)


def test_duplicate_transaction_reference_rejected(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        event_id, account_id, category_id = _ids(app)
        IncomeService.record_income(event_id, category_id, account_id, 'Refund', 'Refund received',
                                    '500', date.today(), 'UPI', user.id, transaction_ref='DUP-INCOME-001')
        with pytest.raises(ValueError, match='already exists'):
            IncomeService.record_income(event_id, category_id, account_id, 'Refund 2', 'Second refund',
                                        '300', date.today(), 'UPI', user.id, transaction_ref='DUP-INCOME-001')
        assert Income.query.count() == 1


def test_income_rolls_back_if_ledger_posting_fails(app, monkeypatch):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        event_id, account_id, category_id = _ids(app)

        def fail(*args, **kwargs):
            raise RuntimeError('ledger failure')

        monkeypatch.setattr('app.services.income_service.LedgerService.record_income', fail)
        with pytest.raises(RuntimeError, match='ledger failure'):
            IncomeService.record_income(event_id, category_id, account_id, 'Refund', 'Refund received',
                                        '500', date.today(), 'CASH', user.id)
        assert Income.query.count() == 0
