from datetime import datetime
from decimal import Decimal
from app.extensions import db

class Vendor(db.Model):
    __tablename__ = 'vendors'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True, index=True)
    category = db.Column(db.String(100), nullable=False)  # e.g., 'Decorations', 'Sound', 'Idol', 'Lighting', 'Catering'
    contact_person = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    
    bank_name = db.Column(db.String(100), nullable=True)
    account_number = db.Column(db.String(50), nullable=True)
    ifsc_code = db.Column(db.String(20), nullable=True)
    upi_id = db.Column(db.String(100), nullable=True)
    gstin = db.Column(db.String(20), nullable=True)
    
    total_paid = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    pending_amount = db.Column(db.Numeric(15, 2), nullable=False, default=Decimal('0.00'))
    is_active = db.Column(db.Boolean, default=True)
    
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Vendor {self.name} ({self.category})>'
