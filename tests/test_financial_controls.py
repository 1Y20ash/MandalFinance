from datetime import date
from decimal import Decimal
import pytest

from app.extensions import db
from app.models.auth import User
from app.models.mandal import Event
from app.models.income import Sponsorship
from app.models.expense import ExpenseCategory, Expense
from app.models.ledger import Account, Transaction
from app.services.financial_controls_service import FinancialControlsService


def login(client, username='admin', password='password'):
    return client.post('/auth/login', data={'username': username, 'password': password})


def test_login_rate_limit(client):
    statuses=[login(client).status_code for _ in range(6)]
    assert statuses[-1]==429


def test_normal_user_cannot_lock_event(client, app):
    login(client,'volunteer','password')
    with app.app_context(): event_id=Event.query.first().id
    response=client.post(f'/finance-controls/events/{event_id}/lock',data={'reason':'attempt'})
    assert response.status_code==403


def test_event_lock_blocks_new_financial_records(app):
    with app.app_context():
        admin=User.query.filter_by(username='admin').first();event=Event.query.first();FinancialControlsService.lock_event(event.id,admin,'Final accounts closed')
        category=ExpenseCategory.query.first();expense=Expense(expense_ref='LOCK-TEST',event_id=event.id,category_id=category.id,title='Blocked',description='Blocked after closure',amount=Decimal('10.00'),expense_date=date.today(),status='SUBMITTED',created_by_id=admin.id)
        db.session.add(expense)
        with pytest.raises(ValueError,match='locked'):db.session.flush()
        db.session.rollback()


def test_sponsorship_receipt_posts_ledger_transaction(app):
    with app.app_context():
        admin=User.query.filter_by(username='admin').first();event=Event.query.first();account=Account.query.first()
        sponsorship=Sponsorship(sponsorship_ref='SP-TEST',event_id=event.id,sponsor_name='Test Sponsor',sponsorship_type='GENERAL',committed_amount=Decimal('1000.00'),received_amount=Decimal('0.00'),pending_amount=Decimal('1000.00'),created_by_id=admin.id)
        db.session.add(sponsorship);db.session.commit();receipt=FinancialControlsService.create_contribution_receipt('SPONSORSHIP',sponsorship.id,account.id,'250.00','CASH',admin)
        txn=db.session.get(Transaction,receipt.transaction_id)
        assert txn.transaction_type=='INCOME' and txn.source_module=='CONTRIBUTION_RECEIPT' and txn.amount==Decimal('250.00') and sponsorship.received_amount==Decimal('250.00')


def test_correction_cannot_self_approve(app):
    with app.app_context():
        admin=User.query.filter_by(username='admin').first();event=Event.query.first();account=Account.query.first()
        txn=Transaction(transaction_ref='TX-COR-TEST',event_id=event.id,account_id=account.id,transaction_type='INCOME',amount=Decimal('10.00'),payment_mode='CASH',description='test',source_module='TEST',source_id=991,created_by_id=admin.id)
        db.session.add(txn);db.session.commit();req=FinancialControlsService.request_correction('TRANSACTION',txn.id,txn.id,'Wrong amount',admin)
        with pytest.raises(ValueError,match='Self-approval'):FinancialControlsService.review_correction(req.id,admin,True,'attempt')


def test_reconciliation_is_decimal(app):
    with app.app_context():
        admin=User.query.filter_by(username='admin').first();account=Account.query.first();record=FinancialControlsService.reconcile_account(account.id,date.today(),'10000.00',admin)
        assert isinstance(record.difference,Decimal) and record.difference==Decimal('0.00')
