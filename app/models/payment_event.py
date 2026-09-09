from datetime import datetime

from app.extensions import db


class PaymentWebhookEvent(db.Model):
    """Minimal payment webhook receipt used for durable idempotency.

    Raw webhook payloads are intentionally not stored because they may contain
    donor/payment metadata. The event ID is the provider-supplied idempotency
    key and is unique at the database layer.
    """

    __tablename__ = 'payment_webhook_events'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(100), nullable=False, unique=True, index=True)
    event_type = db.Column(db.String(80), nullable=False)
    order_id = db.Column(db.String(100), nullable=True, index=True)
    payment_id = db.Column(db.String(100), nullable=True, index=True)
    donation_id = db.Column(db.Integer, db.ForeignKey('donations.id'), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default='PROCESSED')
    processed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('PROCESSED', 'IGNORED')",
            name='ck_payment_webhook_events_status',
        ),
    )

    donation = db.relationship('Donation', backref=db.backref('payment_webhook_events', lazy=True))
