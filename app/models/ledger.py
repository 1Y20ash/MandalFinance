from datetime import datetime
from decimal import Decimal

from sqlalchemy import Index

from app.extensions import db


class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    account_type = db.Column(db.String(20), nullable=False)
    account_number = db.Column(db.String(50), nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)
    ifsc_code = db.Column(db.String(20), nullable=True)
    upi_id = db.Column(db.String(100), nullable=True)
    opening_balance = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    current_balance = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint("account_type IN ('cash', 'bank', 'upi')", name='ck_accounts_account_type'),
        db.CheckConstraint('opening_balance >= 0', name='ck_accounts_opening_balance_nonnegative'),
    )

    def __repr__(self):
        return f'<Account {self.name} ({self.account_type})>'


class TransactionCategory(db.Model):
    __tablename__ = 'transaction_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('name', 'category_type', name='uq_transaction_categories_name_type'),
        db.CheckConstraint("category_type IN ('income', 'expense', 'transfer')", name='ck_transaction_categories_type'),
    )

    def __repr__(self):
        return f'<TransactionCategory {self.name} ({self.category_type})>'


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    transaction_ref = db.Column(db.String(50), unique=True, nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('transaction_categories.id'), nullable=True, index=True)

    transaction_type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    payment_mode = db.Column(db.String(30), nullable=False)
    external_ref = db.Column(db.String(100), nullable=True, index=True)

    description = db.Column(db.Text, nullable=False)
    source_module = db.Column(db.String(30), nullable=False, index=True)
    source_id = db.Column(db.Integer, nullable=True, index=True)

    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    is_reversed = db.Column(db.Boolean, default=False, nullable=False)
    reversed_by_txn_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    reversal_reason = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.CheckConstraint(
            "transaction_type IN ('INCOME', 'EXPENSE', 'TRANSFER', 'REVERSAL')",
            name='ck_transactions_type',
        ),
        db.CheckConstraint('amount > 0', name='ck_transactions_amount_positive'),
        db.CheckConstraint(
            "payment_mode IN ('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE', 'GATEWAY')",
            name='ck_transactions_payment_mode',
        ),
        db.CheckConstraint(
            "is_reversed = FALSE OR reversed_by_txn_id IS NOT NULL",
            name='ck_transactions_reversed_has_reversal',
        ),
        db.CheckConstraint(
            "transaction_type <> 'REVERSAL' OR external_ref LIKE 'REVERSAL-OF-%'",
            name='ck_transactions_reversal_reference',
        ),
        db.Index('ix_transactions_source', 'source_module', 'source_id'),
        db.Index('ix_transactions_account_date', 'account_id', 'transaction_date'),
        Index(
            'uq_transactions_active_source', 'source_module', 'source_id',
            unique=True,
            postgresql_where=db.text('source_id IS NOT NULL AND is_reversed = FALSE'),
            sqlite_where=db.text('source_id IS NOT NULL AND is_reversed = 0'),
        ),
        Index(
            'uq_transactions_external_ref', 'external_ref',
            unique=True,
            postgresql_where=db.text('external_ref IS NOT NULL'),
            sqlite_where=db.text('external_ref IS NOT NULL'),
        ),
    )

    account = db.relationship('Account', backref=db.backref('transactions', lazy=True))
    category = db.relationship('TransactionCategory', backref=db.backref('transactions', lazy=True))
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def __repr__(self):
        return f'<Transaction {self.transaction_ref} - {self.transaction_type} {self.amount}>'
