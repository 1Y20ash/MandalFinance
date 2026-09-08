import pytest
from datetime import date
from decimal import Decimal

from app.extensions import db
from app.models.audit import AuditLog
from app.models.auth import User
from app.models.expense import ExpenseCategory, Expense
from app.models.ledger import Account, Transaction
from app.models.mandal import Event
from app.services.expense_service import ExpenseService


def test_expense_submission_creates_pending_record_and_audit(app):
    with app.app_context():
        volunteer = User.query.filter_by(username='volunteer').first()
        event = Event.query.first()
        category = ExpenseCategory.query.first()

        expense = ExpenseService.submit_expense(
            event_id=event.id, category_id=category.id,
            title='Decoration material', description='Festival decoration purchase',
            amount='1250.50', expense_date=date(2026, 9, 1), created_by_user=volunteer,
        )

        assert expense.expense_ref.startswith('EXP-2026-')
        assert expense.amount == Decimal('1250.50')
        assert expense.status == 'SUBMITTED'
        assert expense.transaction_id is None
        assert AuditLog.query.filter_by(
            entity_type='EXPENSE', entity_id=str(expense.id), action='CREATE'
        ).count() == 1


def test_expense_submission_rejects_invalid_amount_without_persisting(app):
    with app.app_context():
        volunteer = User.query.filter_by(username='volunteer').first()
        event = Event.query.first()
        category = ExpenseCategory.query.first()
        before = Expense.query.count()

        with pytest.raises(ValueError, match='greater than zero'):
            ExpenseService.submit_expense(
                event_id=event.id, category_id=category.id,
                title='Invalid expense', description='Invalid amount test',
                amount='0', expense_date=date.today(), created_by_user=volunteer,
            )

        assert Expense.query.count() == before


def test_expense_submission_rejects_inactive_category(app):
    with app.app_context():
        volunteer = User.query.filter_by(username='volunteer').first()
        event = Event.query.first()
        category = ExpenseCategory.query.first()
        category.is_active = False
        db.session.commit()

        with pytest.raises(ValueError, match='not active'):
            ExpenseService.submit_expense(
                event_id=event.id, category_id=category.id,
                title='Decoration', description='Inactive category test',
                amount='100', expense_date=date.today(), created_by_user=volunteer,
            )


def test_expense_payment_requires_reference_and_posts_ledger_atomically(app):
    with app.app_context():
        volunteer = User.query.filter_by(username='volunteer').first()
        admin = User.query.filter_by(username='admin').first()
        event = Event.query.first()
        category = ExpenseCategory.query.first()
        account = Account.query.first()

        expense = ExpenseService.submit_expense(
            event_id=event.id, category_id=category.id,
            title='Sound rental', description='Festival sound rental',
            amount='500.00', expense_date=date.today(), created_by_user=volunteer,
        )
        ExpenseService.approve_expense(expense.id, admin)

        with pytest.raises(ValueError, match='Payment reference'):
            ExpenseService.pay_expense(expense.id, admin, account.id, 'UPI')

        db.session.refresh(expense)
        assert expense.status == 'APPROVED'
        assert expense.transaction_id is None

        ExpenseService.pay_expense(
            expense.id, admin, account.id, 'UPI', payment_ref='UTR-EXP-001'
        )
        db.session.refresh(expense)
        assert expense.status == 'PAID'
        assert expense.transaction_id is not None

        txn = db.session.get(Transaction, expense.transaction_id)
        assert txn.transaction_type == 'EXPENSE'
        assert txn.source_module == 'EXPENSE'
        assert txn.source_id == expense.id
        assert txn.amount == Decimal('500.00')


def test_duplicate_payment_reference_is_rejected(app):
    with app.app_context():
        volunteer = User.query.filter_by(username='volunteer').first()
        admin = User.query.filter_by(username='admin').first()
        event = Event.query.first()
        category = ExpenseCategory.query.first()
        account = Account.query.first()

        first = ExpenseService.submit_expense(
            event_id=event.id, category_id=category.id, title='First purchase',
            description='First expense', amount='100', expense_date=date.today(), created_by_user=volunteer,
        )
        ExpenseService.approve_expense(first.id, admin)
        ExpenseService.pay_expense(first.id, admin, account.id, 'BANK_TRANSFER', payment_ref='BANK-001')

        second = ExpenseService.submit_expense(
            event_id=event.id, category_id=category.id, title='Second purchase',
            description='Second expense', amount='200', expense_date=date.today(), created_by_user=volunteer,
        )
        ExpenseService.approve_expense(second.id, admin)

        with pytest.raises(ValueError, match='payment reference already exists'):
            ExpenseService.pay_expense(second.id, admin, account.id, 'BANK_TRANSFER', payment_ref='BANK-001')


def test_self_approval_is_forbidden_even_for_admin(app):
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        event = Event.query.first()
        category = ExpenseCategory.query.first()

        expense = ExpenseService.submit_expense(
            event_id=event.id, category_id=category.id,
            title='Admin submitted expense', description='Segregation of duties test',
            amount='100.00', expense_date=date.today(), created_by_user=admin,
        )

        with pytest.raises(ValueError, match='Self-approval is not allowed'):
            ExpenseService.approve_expense(expense.id, admin)

        db.session.refresh(expense)
        assert expense.status == 'SUBMITTED'


def test_closed_event_rejects_new_or_pending_expense_actions(app):
    with app.app_context():
        volunteer = User.query.filter_by(username='volunteer').first()
        admin = User.query.filter_by(username='admin').first()
        event = Event.query.first()
        category = ExpenseCategory.query.first()

        event.status = 'CLOSED'
        db.session.commit()

        with pytest.raises(ValueError, match='locked'):
            ExpenseService.submit_expense(
                event_id=event.id, category_id=category.id,
                title='Closed event expense', description='Should not be accepted',
                amount='100.00', expense_date=date.today(), created_by_user=volunteer,
            )


def test_rejection_is_also_segregated_from_creator(app):
    with app.app_context():
        volunteer = User.query.filter_by(username='volunteer').first()
        event = Event.query.first()
        category = ExpenseCategory.query.first()

        expense = ExpenseService.submit_expense(
            event_id=event.id, category_id=category.id,
            title='Review test', description='Creator cannot review own expense',
            amount='100.00', expense_date=date.today(), created_by_user=volunteer,
        )

        with pytest.raises(ValueError, match='Self-review is not allowed'):
            ExpenseService.reject_expense(expense.id, volunteer, 'Rejecting own submission')

        db.session.refresh(expense)
        assert expense.status == 'SUBMITTED'
