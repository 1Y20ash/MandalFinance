from datetime import datetime

from app.extensions import db


class DeletionRequest(db.Model):
    __tablename__ = 'deletion_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    requested_by_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
    )
    status = db.Column(db.String(20), nullable=False, default='PENDING', index=True)
    reason = db.Column(db.Text, nullable=True)
    decision_reason = db.Column(db.Text, nullable=True)
    legal_hold = db.Column(db.Boolean, nullable=False, default=False)
    legal_hold_reason = db.Column(db.Text, nullable=True)
    requested_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', foreign_keys=[user_id])
    requested_by = db.relationship('User', foreign_keys=[requested_by_id])

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'BLOCKED', 'COMPLETED')",
            name='ck_deletion_requests_status',
        ),
        db.CheckConstraint(
            '(legal_hold = FALSE) OR (length(trim(coalesce(legal_hold_reason, \'\'))) > 0)',
            name='ck_deletion_requests_hold_reason',
        ),
    )

    def __repr__(self):
        return f'<DeletionRequest #{self.id} {self.status} user={self.user_id}>'
