import pytest
from datetime import date
from decimal import Decimal
from app.models.auth import User
from app.models.mandal import Event
from app.models.expense import ExpenseCategory, Expense
from app.models.ledger import Account
from app.services.expense_service import ExpenseService

def test_expense_submission_approval_and_payment_flow(app):
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        volunteer = User.query.filter_by(username='volunteer').first()
        event = Event.query.first()
        category = ExpenseCategory.query.first()
        account = Account.query.first()

        # Step 1: Volunteer submits expense
        expense = ExpenseService.submit_expense(
            event_id=event.id,
            category_id=category.id,
            title='Lighting Setup',
            description='Pandol lighting',
            amount='2500.00',
            expense_date=date.today(),
            created_by_user=volunteer
        )

        assert expense.status == 'SUBMITTED'
        assert expense.expense_ref.startswith('EXP-')

        # Step 2: Prevent Volunteer self-approval (if non-admin)
        with pytest.raises(ValueError, match="Self-approval is not allowed"):
            ExpenseService.approve_expense(expense.id, volunteer)

        # Step 3: Admin approves expense
        ExpenseService.approve_expense(expense.id, admin, comments='Approved by Admin')
        assert expense.status == 'APPROVED'

        # Step 4: Disburse payment
        ExpenseService.pay_expense(expense.id, admin, account.id, 'CASH', 'REF-1001')
        assert expense.status == 'PAID'
        assert expense.transaction_id is not None
