from datetime import datetime
from decimal import Decimal
from app.extensions import db


class BudgetCategory(db.Model):
    __tablename__ = 'budget_categories'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    expense_category_id = db.Column(db.Integer, db.ForeignKey('expense_categories.id'), nullable=False)
    allocated_amount = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    spent_amount = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    warning_threshold_pct = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('75.00'))
    high_warning_threshold_pct = db.Column(db.Numeric(5, 2), nullable=False, default=Decimal('90.00'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    event = db.relationship('Event', backref=db.backref('budget_categories', lazy=True))
    expense_category = db.relationship('ExpenseCategory', backref=db.backref('budgets', lazy=True))

    @property
    def remaining_amount(self):
        return self.allocated_amount - self.spent_amount

    @property
    def utilization_percentage(self):
        if self.allocated_amount > Decimal('0.00'):
            return (self.spent_amount / self.allocated_amount) * Decimal('100.00')
        return Decimal('0.00')

    @property
    def alert_status(self):
        pct = self.utilization_percentage
        if pct > Decimal('100.00'):
            return 'EXCEEDED'
        if pct >= self.high_warning_threshold_pct:
            return 'HIGH_WARNING'
        if pct >= self.warning_threshold_pct:
            return 'WARNING'
        return 'NORMAL'


class Budget(db.Model):
    __tablename__ = 'budgets'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, unique=True)
    total_income_target = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    total_expense_limit = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    actual_income = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    actual_expense = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    status = db.Column(db.String(20), nullable=False, default='DRAFT')
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    revision_no = db.Column(db.Integer, nullable=False, default=1)
    revision_reason = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event = db.relationship('Event', backref=db.backref('budget', uselist=False))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])

    @property
    def net_budgeted_balance(self):
        return self.total_income_target - self.total_expense_limit

    @property
    def actual_balance(self):
        return self.actual_income - self.actual_expense

    @property
    def is_editable(self):
        return self.status in {'DRAFT', 'REVISED'}
