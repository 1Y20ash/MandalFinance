from datetime import datetime
from decimal import Decimal
from app.extensions import db

class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # e.g., "Main Cash Box", "SBI Bank Account", "Mandal UPI"
    account_type = db.Column(db.String(20), nullable=False)  # 'cash', 'bank', 'upi'
    account_number = db.Column(db.String(50), nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)
    ifsc_code = db.Column(db.String(20), nullable=True)
    upi_id = db.Column(db.String(100), nullable=True)
    opening_balance = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    current_balance = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Account {self.name} ({self.account_type})>'


class TransactionCategory(db.Model):
    __tablename__ = 'transaction_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_type = db.Column(db.String(20), nullable=False)  # 'income', 'expense', 'transfer'
    description = db.Column(db.String(255), nullable=True)
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<TransactionCategory {self.name} ({self.category_type})>'


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    transaction_ref = db.Column(db.String(50), unique=True, nullable=False, index=True)  # TXN-YYYYMMDD-XXXX
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('transaction_categories.id'), nullable=True)
    
    transaction_type = db.Column(db.String(20), nullable=False)  # 'INCOME', 'EXPENSE', 'TRANSFER', 'REVERSAL'
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    payment_mode = db.Column(db.String(30), nullable=False)  # 'CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE', 'GATEWAY'
    external_ref = db.Column(db.String(100), nullable=True)  # UPI UTR, Cheque No, Gateway Payment ID
    
    description = db.Column(db.Text, nullable=False)
    source_module = db.Column(db.String(30), nullable=False)  # 'DONATION', 'SPONSORSHIP', 'MEMBER', 'EXPENSE', 'MANUAL'
    source_id = db.Column(db.Integer, nullable=True)  # ID of linked record in source module
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_reversed = db.Column(db.Boolean, default=False)
    reversed_by_txn_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    reversal_reason = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    account = db.relationship('Account', backref=db.backref('transactions', lazy=True))
    category = db.relationship('TransactionCategory', backref=db.backref('transactions', lazy=True))
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    def __repr__(self):
        return f'<Transaction {self.transaction_ref} - {self.transaction_type} {self.amount}>'
