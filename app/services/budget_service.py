from decimal import Decimal
from sqlalchemy import func
from app.extensions import db
from app.models.budget import Budget, BudgetCategory
from app.models.ledger import Transaction
from app.models.expense import Expense


class BudgetService:
    @staticmethod
    def recalculate_event_budget(event_id):
        """Derive budget actuals from finalized central-ledger transactions."""
        budget = Budget.query.filter_by(event_id=event_id).first()
        if not budget:
            return None
        categories = BudgetCategory.query.filter_by(event_id=event_id).all()
        for bcat in categories:
            expense_ids = db.session.query(Expense.id).filter(
                Expense.event_id == event_id,
                Expense.category_id == bcat.expense_category_id,
                Expense.status == 'PAID',
            ).subquery()
            spent = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
                Transaction.event_id == event_id,
                Transaction.source_module == 'EXPENSE',
                Transaction.source_id.in_(expense_ids),
                Transaction.transaction_type == 'EXPENSE',
                Transaction.is_reversed.is_(False),
            ).scalar()
            bcat.spent_amount = Decimal(str(spent or '0')).quantize(Decimal('0.01'))
        income = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.event_id == event_id,
            Transaction.transaction_type == 'INCOME',
            Transaction.is_reversed.is_(False),
        ).scalar()
        expense = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.event_id == event_id,
            Transaction.transaction_type == 'EXPENSE',
            Transaction.is_reversed.is_(False),
        ).scalar()
        budget.actual_income = Decimal(str(income or '0')).quantize(Decimal('0.01'))
        budget.actual_expense = Decimal(str(expense or '0')).quantize(Decimal('0.01'))
        db.session.commit()
        return budget
