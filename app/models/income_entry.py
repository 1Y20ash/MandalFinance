from datetime import datetime
from decimal import Decimal

from app.extensions import db


class Income(db.Model):
    __tablename__ = 'income_entries'

    id = db.Column(db.Integer, primary_key=True)
    income_ref = db.Column(db.String(50), unique=True, nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('transaction_categories.id'), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False, index=True)

    source_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    income_date = db.Column(db.Date, nullable=False, index=True)
    payment_mode = db.Column(db.String(30), nullable=False)
    transaction_ref = db.Column(db.String(100), nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)

    # Nullable is intentional at the database/ORM insertion boundary: the
    # income row must receive its primary key before the central ledger row
    # can reference income.id as its source_id. IncomeService performs both
    # inserts in one transaction and assigns this field before commit.
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True, unique=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    event = db.relationship('Event', backref=db.backref('income_entries', lazy=True))
    category = db.relationship('TransactionCategory', backref=db.backref('income_entries', lazy=True))
    account = db.relationship('Account', backref=db.backref('income_entries', lazy=True))
    transaction = db.relationship('Transaction', foreign_keys=[transaction_id])
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    __table_args__ = (
        db.CheckConstraint('amount > 0', name='ck_income_entries_amount_positive'),
        db.CheckConstraint("payment_mode IN ('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE')", name='ck_income_entries_payment_mode'),
    )

    def __repr__(self):
        return f'<Income {self.income_ref} - {self.source_name} ₹{self.amount}>'
