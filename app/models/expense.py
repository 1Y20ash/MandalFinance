from datetime import datetime
from decimal import Decimal

from sqlalchemy import Index

from app.extensions import db


class ExpenseCategory(db.Model):
    __tablename__ = 'expense_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<ExpenseCategory {self.name}>'


class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    expense_ref = db.Column(db.String(50), unique=True, nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('expense_categories.id'), nullable=False, index=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=True, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True, index=True)

    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    expense_date = db.Column(db.Date, nullable=False, index=True)

    bill_number = db.Column(db.String(100), nullable=True, index=True)
    bill_date = db.Column(db.Date, nullable=True)
    payment_mode = db.Column(db.String(30), nullable=True)
    payment_ref = db.Column(db.String(100), nullable=True, index=True)
    payment_date = db.Column(db.DateTime, nullable=True)

    status = db.Column(db.String(20), nullable=False, default='SUBMITTED', index=True)

    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    paid_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    approval_date = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.CheckConstraint('amount > 0', name='ck_expenses_amount_positive'),
        db.CheckConstraint(
            "status IN ('SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'PAID')",
            name='ck_expenses_status',
        ),
        db.CheckConstraint(
            "payment_mode IS NULL OR payment_mode IN ('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE')",
            name='ck_expenses_payment_mode',
        ),
        Index(
            'uq_expenses_payment_ref', 'payment_ref',
            unique=True,
            postgresql_where=db.text('payment_ref IS NOT NULL'),
            sqlite_where=db.text('payment_ref IS NOT NULL'),
        ),
    )

    event = db.relationship('Event', backref=db.backref('expenses', lazy=True))
    category = db.relationship('ExpenseCategory', backref=db.backref('expenses', lazy=True))
    vendor = db.relationship('Vendor', backref=db.backref('expenses', lazy=True))
    account = db.relationship('Account', backref=db.backref('expenses', lazy=True))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    approved_by = db.relationship('User', foreign_keys=[approved_by_id])
    paid_by = db.relationship('User', foreign_keys=[paid_by_id])
    transaction = db.relationship('Transaction', foreign_keys=[transaction_id])

    approvals = db.relationship('Approval', backref='expense', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Expense {self.expense_ref} - {self.title} ₹{self.amount} [{self.status}]>'


class Approval(db.Model):
    __tablename__ = 'approvals'

    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id', ondelete='CASCADE'), nullable=False, index=True)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    action = db.Column(db.String(20), nullable=False)
    previous_status = db.Column(db.String(20), nullable=False)
    new_status = db.Column(db.String(20), nullable=False)
    comments = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    approver = db.relationship('User', foreign_keys=[approver_id])

    def __repr__(self):
        return f'<Approval Expense #{self.expense_id}: {self.action} by User #{self.approver_id}>'
