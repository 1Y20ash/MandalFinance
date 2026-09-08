from datetime import datetime
from decimal import Decimal
from app.extensions import db


class ReconciliationLine(db.Model):
    __tablename__ = 'reconciliation_lines'

    id = db.Column(db.Integer, primary_key=True)
    reconciliation_id = db.Column(db.Integer, db.ForeignKey('reconciliation_records.id', ondelete='CASCADE'), nullable=False, index=True)
    line_ref = db.Column(db.String(80), nullable=False)
    transaction_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=True)
    external_ref = db.Column(db.String(100), nullable=True, index=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    matched_transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default='UNMATCHED')
    match_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('reconciliation_id', 'line_ref', name='uq_reconciliation_line_ref'),
        db.CheckConstraint('amount > 0', name='ck_reconciliation_line_amount_positive'),
        db.CheckConstraint("status IN ('UNMATCHED', 'MATCHED', 'IGNORED')", name='ck_reconciliation_line_status'),
    )

    reconciliation = db.relationship('ReconciliationRecord', backref=db.backref('lines', lazy=True, cascade='all, delete-orphan'))
    matched_transaction = db.relationship('Transaction')

    @property
    def is_matched(self):
        return self.status == 'MATCHED' and self.matched_transaction_id is not None
