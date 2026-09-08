from datetime import datetime
from decimal import Decimal
from app.extensions import db


class Mandal(db.Model):
    __tablename__ = 'mandals'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, default='Shree Ashtavinayak Ganesh Utsav Mandal')
    location = db.Column(db.String(255), nullable=False, default='Panchasheel Nagar, Gittikhadan, Nagpur, Maharashtra, India')
    registration_number = db.Column(db.String(100), nullable=True)
    contact_phone = db.Column(db.String(20), nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    events = db.relationship('Event', backref='mandal', lazy=True)


class FinancialYear(db.Model):
    __tablename__ = 'financial_years'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_locked = db.Column(db.Boolean, default=False, nullable=False)
    locked_at = db.Column(db.DateTime, nullable=True)
    locked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    opening_balance = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.CheckConstraint('start_date <= end_date', name='ck_financial_year_dates'),)
    events = db.relationship('Event', backref='financial_year', lazy=True)
    locked_by = db.relationship('User', foreign_keys=[locked_by_id])


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    mandal_id = db.Column(db.Integer, db.ForeignKey('mandals.id'), nullable=False, index=True)
    financial_year_id = db.Column(db.Integer, db.ForeignKey('financial_years.id'), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    year = db.Column(db.Integer, nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), nullable=False, default='OPEN')
    locked_at = db.Column(db.DateTime, nullable=True)
    locked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    closure_reason = db.Column(db.Text, nullable=True)
    budget_target = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        db.CheckConstraint('start_date <= end_date', name='ck_events_dates'),
        db.CheckConstraint('budget_target >= 0', name='ck_events_budget_target_nonnegative'),
        db.CheckConstraint("status IN ('OPEN', 'CLOSED', 'LOCKED')", name='ck_events_status'),
        db.Index('ix_events_mandal_year', 'mandal_id', 'year'),
    )
    locked_by = db.relationship('User', foreign_keys=[locked_by_id])

    @property
    def is_editable(self):
        return self.status == 'OPEN' and not (self.financial_year and self.financial_year.is_locked)

    def assert_editable(self):
        if not self.is_editable:
            raise ValueError('This event or its financial year is locked; financial records cannot be modified.')

    def __repr__(self):
        return f'<Event {self.title}>'
