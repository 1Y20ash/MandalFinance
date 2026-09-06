from decimal import Decimal
from app.extensions import db
from app.models.budget import Budget, BudgetCategory
from app.models.expense import Expense

class BudgetService:
    @staticmethod
    def recalculate_event_budget(event_id):
        """
        Recalculates spent amounts for budget categories from paid/approved expenses.
        """
        budget = Budget.query.filter_by(event_id=event_id).first()
        if not budget:
            return None

        categories = BudgetCategory.query.filter_by(event_id=event_id).all()
        total_actual_expense = Decimal('0.00')

        for bcat in categories:
            # Sum paid expenses for this category
            paid_expenses = Expense.query.filter(
                Expense.event_id == event_id,
                Expense.category_id == bcat.expense_category_id,
                Expense.status == 'PAID'
            ).all()

            spent = sum(e.amount for e in paid_expenses)
            bcat.spent_amount = spent
            total_actual_expense += spent

        budget.actual_expense = total_actual_expense
        db.session.commit()

        return budget
