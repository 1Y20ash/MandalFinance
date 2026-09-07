from datetime import datetime, date
from decimal import Decimal
from app.extensions import db


class ContributionReceipt(db.Model):
    __tablename__ = 'contribution_receipts'
    id = db.Column(db.Integer, primary_key=True)
    receipt_ref = db.Column(db.String(60), unique=True, nullable=False, index=True)
    source_type = db.Column(db.String(20), nullable=False)  # SPONSORSHIP / MEMBER
    source_id = db.Column(db.Integer, nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_mode = db.Column(db.String(30), nullable=False)
    external_ref = db.Column(db.String(100), nullable=True, index=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True, unique=True)
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (
        db.CheckConstraint("source_type IN ('SPONSORSHIP', 'MEMBER')", name='ck_contribution_receipts_source_type'),
        db.CheckConstraint('amount > 0', name='ck_contribution_receipts_amount_positive'),
        db.CheckConstraint("payment_mode IN ('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE', 'GATEWAY')", name='ck_contribution_receipts_payment_mode'),
    )
    event = db.relationship('Event')
    account = db.relationship('Account')
    transaction = db.relationship('Transaction')
    created_by = db.relationship('User')


class CorrectionRequest(db.Model):
    __tablename__ = 'correction_requests'
    id = db.Column(db.Integer, primary_key=True)
    request_ref = db.Column(db.String(60), unique=True, nullable=False, index=True)
    entity_type = db.Column(db.String(40), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False, index=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='PENDING')
    requested_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    review_note = db.Column(db.Text, nullable=True)
    applied_reversal_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    __table_args__ = (db.CheckConstraint("status IN ('PENDING', 'APPROVED', 'REJECTED', 'APPLIED')", name='ck_correction_status'),)
    transaction = db.relationship('Transaction', foreign_keys=[transaction_id])
    reversal = db.relationship('Transaction', foreign_keys=[applied_reversal_id])
    requested_by = db.relationship('User', foreign_keys=[requested_by_id])
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])


class ReconciliationRecord(db.Model):
    __tablename__ = 'reconciliation_records'
    id = db.Column(db.Integer, primary_key=True)
    reconciliation_ref = db.Column(db.String(60), unique=True, nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True, index=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False, index=True)
    statement_date = db.Column(db.Date, nullable=False)
    period_start = db.Column(db.Date, nullable=True)
    period_end = db.Column(db.Date, nullable=True)
    book_balance = db.Column(db.Numeric(15, 2), nullable=False)
    statement_balance = db.Column(db.Numeric(15, 2), nullable=False)
    difference = db.Column(db.Numeric(15, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='OPEN')
    external_reference = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    __table_args__ = (db.CheckConstraint("status IN ('OPEN', 'MATCHED', 'ADJUSTMENT_REQUIRED', 'RESOLVED')", name='ck_reconciliation_status'),)
    account = db.relationship('Account')
    event = db.relationship('Event')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    resolved_by = db.relationship('User', foreign_keys=[resolved_by_id])


class EvidenceRule(db.Model):
    __tablename__ = 'evidence_rules'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    entity_type = db.Column(db.String(40), nullable=False)
    min_amount = db.Column(db.Numeric(15, 2), nullable=True)
    required_categories = db.Column(db.Text, nullable=False)  # JSON array stored as text
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.relationship('User')
