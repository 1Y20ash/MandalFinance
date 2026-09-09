from datetime import datetime
from decimal import Decimal
from app.extensions import db


class Donation(db.Model):
    __tablename__ = 'donations'
    id = db.Column(db.Integer, primary_key=True)
    donation_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    donor_name = db.Column(db.String(120), nullable=False)
    donor_phone = db.Column(db.String(20), nullable=True)
    donor_email = db.Column(db.String(120), nullable=True)
    donor_address = db.Column(db.Text, nullable=True)
    pan_number = db.Column(db.String(20), nullable=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    purpose = db.Column(db.String(150), nullable=False, default='General Donation')
    donation_type = db.Column(db.String(20), nullable=False, default='OFFLINE')
    payment_mode = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='PENDING')
    gateway_order_id = db.Column(db.String(100), nullable=True, unique=True, index=True)
    gateway_payment_id = db.Column(db.String(100), nullable=True, unique=True, index=True)
    gateway_signature = db.Column(db.String(255), nullable=True)
    transaction_ref = db.Column(db.String(100), nullable=True, index=True)
    receipt_number = db.Column(db.String(50), unique=True, nullable=True, index=True)
    receipt_generated_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    event = db.relationship('Event', backref=db.backref('donations', lazy=True))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    __table_args__ = (
        db.CheckConstraint('amount > 0', name='ck_donations_amount_positive'),
        db.CheckConstraint("donation_type IN ('ONLINE', 'OFFLINE')", name='ck_donations_type'),
        db.CheckConstraint("payment_mode IN ('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE', 'ONLINE_GATEWAY')", name='ck_donations_payment_mode'),
        db.CheckConstraint("status IN ('PENDING', 'SUCCESS', 'FAILED', 'CANCELLED')", name='ck_donations_status'),
    )
    def __repr__(self):
        return f'<Donation {self.donation_number} - {self.donor_name} ₹{self.amount}>'


class Sponsorship(db.Model):
    __tablename__ = 'sponsorships'
    id = db.Column(db.Integer, primary_key=True)
    sponsorship_ref = db.Column(db.String(50), unique=True, nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    sponsor_name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(100), nullable=True)
    contact_phone = db.Column(db.String(20), nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    sponsorship_type = db.Column(db.String(100), nullable=False)
    committed_amount = db.Column(db.Numeric(15, 2), nullable=False)
    received_amount = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    pending_amount = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    status = db.Column(db.String(20), nullable=False, default='COMMITTED')
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    event = db.relationship('Event', backref=db.backref('sponsorships', lazy=True))
    created_by = db.relationship('User', foreign_keys=[created_by_id])


class MemberContribution(db.Model):
    __tablename__ = 'member_contributions'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    member_name = db.Column(db.String(120), nullable=False)
    member_phone = db.Column(db.String(20), nullable=True)
    designation = db.Column(db.String(100), nullable=True)
    target_amount = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    received_amount = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    pending_amount = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    payment_mode = db.Column(db.String(30), nullable=True)
    transaction_ref = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='PENDING')
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    event = db.relationship('Event', backref=db.backref('member_contributions', lazy=True))
    created_by = db.relationship('User', foreign_keys=[created_by_id])
