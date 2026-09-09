from datetime import datetime
from app.extensions import db


class ConsentRecord(db.Model):
    __tablename__ = 'consent_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    purpose = db.Column(db.String(100), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='GRANTED')
    notice_version = db.Column(db.String(40), nullable=False)
    source = db.Column(db.String(40), nullable=False, default='web')
    granted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    withdrawn_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint("status IN ('GRANTED', 'WITHDRAWN')", name='ck_consent_status'),
        db.UniqueConstraint('user_id', 'purpose', 'notice_version', name='uq_consent_user_purpose_version'),
    )


class PrivacyRequest(db.Model):
    __tablename__ = 'privacy_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    request_type = db.Column(db.String(30), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default='REQUESTED', index=True)
    details = db.Column(db.Text, nullable=True)
    response_note = db.Column(db.Text, nullable=True)
    requested_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint(
            "request_type IN ('ACCESS', 'CORRECTION', 'DELETION', 'WITHDRAW_CONSENT', 'GRIEVANCE')",
            name='ck_privacy_request_type',
        ),
        db.CheckConstraint(
            "status IN ('REQUESTED', 'IDENTITY_VERIFIED', 'REVIEWED', 'PROCESSED', 'COMPLETED', 'REJECTED')",
            name='ck_privacy_request_status',
        ),
    )

    requester = db.relationship('User', foreign_keys=[user_id], backref=db.backref('privacy_requests', lazy=True))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by_id])
