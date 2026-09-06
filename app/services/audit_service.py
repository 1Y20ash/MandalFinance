from flask import request
from flask_login import current_user
from app.extensions import db
from app.models.audit import AuditLog

class AuditService:
    @staticmethod
    def log_action(action, entity_type, entity_id=None, description="", details=None, user_override=None):
        """
        Creates an immutable audit log entry for system actions.
        """
        user_id = None
        user_email = None
        
        if user_override:
            user_id = user_override.id
            user_email = user_override.email
        elif current_user and current_user.is_authenticated:
            user_id = current_user.id
            user_email = current_user.email
            
        ip_address = None
        user_agent = None
        if request:
            ip_address = request.remote_addr
            user_agent = str(request.user_agent)[:250] if request.user_agent else None
            
        audit_entry = AuditLog(
            user_id=user_id,
            user_email=user_email,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            description=description,
            details=str(details) if details else None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(audit_entry)
        db.session.commit()
        return audit_entry
