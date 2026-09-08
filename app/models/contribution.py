from datetime import datetime
from decimal import Decimal

from app.extensions import db


class SponsorshipPayment(db.Model):
    __tablename__ = 'sponsorship_payments'

    id = db.Column(db.Integer, primary_key=True)
    sponsorship_id = db.Column(db.Integer, db.ForeignKey('sponsorships.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    payment_mode = db.Column(db.String(30), nullable=False)
    transaction_ref = db.Column(db.String(100), nullable=True, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    ledger_transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True, unique=True)
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    sponsorship = db.relationship('Sponsorship', backref=db.backref('payments', lazy=True, cascade='all, delete-orphan'))
    account = db.relationship('Account')
    ledger_transaction = db.relationship('Transaction')
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    __table_args__ = (
        db.CheckConstraint('amount > 0', name='ck_sponsorship_payment_amount_positive'),
        db.CheckConstraint("payment_mode IN ('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE', 'GATEWAY')", name='ck_sponsorship_payment_mode'),
        db.UniqueConstraint('sponsorship_id', 'transaction_ref', name='uq_sponsorship_payment_ref'),
    )


class MemberContributionPayment(db.Model):
    __tablename__ = 'member_contribution_payments'

    id = db.Column(db.Integer, primary_key=True)
    contribution_id = db.Column(db.Integer, db.ForeignKey('member_contributions.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    payment_mode = db.Column(db.String(30), nullable=False)
    transaction_ref = db.Column(db.String(100), nullable=True, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    ledger_transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True, unique=True)
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    contribution = db.relationship('MemberContribution', backref=db.backref('payments', lazy=True, cascade='all, delete-orphan'))
    account = db.relationship('Account')
    ledger_transaction = db.relationship('Transaction')
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    __table_args__ = (
        db.CheckConstraint('amount > 0', name='ck_member_payment_amount_positive'),
        db.CheckConstraint("payment_mode IN ('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE', 'GATEWAY')", name='ck_member_payment_mode'),
        db.UniqueConstraint('contribution_id', 'transaction_ref', name='uq_member_payment_ref'),
    )
