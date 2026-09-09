from datetime import datetime

from app.extensions import db


class WebhookEvent(db.Model):
    __tablename__ = 'webhook_events'

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(40), nullable=False)
    event_id = db.Column(db.String(120), nullable=False)
    event_type = db.Column(db.String(100), nullable=False)
    received_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('provider', 'event_id', name='uq_webhook_events_provider_event'),
        db.Index('ix_webhook_events_provider_type', 'provider', 'event_type'),
    )
