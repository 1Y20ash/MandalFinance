from datetime import datetime, timedelta

from app.extensions import db


class RetentionPolicy(db.Model):
    __tablename__ = 'retention_policies'

    id = db.Column(db.Integer, primary_key=True)
    data_category = db.Column(db.String(80), unique=True, nullable=False, index=True)
    retention_days = db.Column(db.Integer, nullable=False)
    retention_basis = db.Column(db.String(120), nullable=False)
    disposal_action = db.Column(db.String(20), nullable=False, default='REVIEW')
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.CheckConstraint('retention_days > 0', name='ck_retention_policies_days_positive'),
        db.CheckConstraint("disposal_action IN ('REVIEW', 'ARCHIVE')", name='ck_retention_policies_action'),
    )

    def expires_at(self, created_at):
        if created_at is None:
            raise ValueError('created_at is required for retention calculation.')
        return created_at + timedelta(days=self.retention_days)

    def __repr__(self):
        return f'<RetentionPolicy {self.data_category}: {self.retention_days} days>'
