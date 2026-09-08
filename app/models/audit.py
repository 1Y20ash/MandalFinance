from datetime import datetime
from app.extensions import db

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user_email = db.Column(db.String(120), nullable=True)
    
    action = db.Column(db.String(50), nullable=False, index=True)  # 'LOGIN', 'CREATE', 'UPDATE', 'APPROVE', 'REJECT', 'PAY', 'UPLOAD', 'VERIFY', 'REVERSE', 'EXPORT'
    entity_type = db.Column(db.String(50), nullable=False, index=True)  # 'USER', 'DONATION', 'EXPENSE', 'DOCUMENT', 'ROLE', 'SETTING'
    entity_id = db.Column(db.String(50), nullable=True)
    
    description = db.Column(db.Text, nullable=False)
    details = db.Column(db.Text, nullable=True)  # JSON string or text metadata
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', foreign_keys=[user_id])

    def __repr__(self):
        return f'<AuditLog [{self.action}] {self.entity_type} #{self.entity_id} by {self.user_email}>'


class Setting(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)
    is_public = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False, default='INFO')  # 'INFO', 'WARNING', 'APPROVAL', 'BUDGET'
    is_read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])
