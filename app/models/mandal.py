from datetime import datetime, date
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
    name = db.Column(db.String(50), nullable=False, unique=True)  # e.g., "FY 2026-2027"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    opening_balance = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    events = db.relationship('Event', backref='financial_year', lazy=True)


class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    mandal_id = db.Column(db.Integer, db.ForeignKey('mandals.id'), nullable=False)
    financial_year_id = db.Column(db.Integer, db.ForeignKey('financial_years.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)  # e.g., "Ganesh Utsav 2026"
    year = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    budget_target = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Event {self.title}>'
