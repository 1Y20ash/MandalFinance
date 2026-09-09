import json
from flask import request
from flask_login import current_user
from app.extensions import db
from app.models.audit import AuditLog


class AuditService:
    MAX_DESCRIPTION_LENGTH = 500
    MAX_DETAILS_LENGTH = 4000

    @staticmethod
    def log_action(action, entity_type, entity_id=None, description="", details=None,
                   user_override=None, commit=True):
        """Create a bounded audit record with only operational metadata."""
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

        if isinstance(details, (dict, list)):
            details_value = json.dumps(details, separators=(',', ':'), default=str)
        else:
            details_value = str(details) if details else None

        audit_entry = AuditLog(
            user_id=user_id,
            user_email=user_email,
            action=str(action)[:100],
            entity_type=str(entity_type)[:100] if entity_type else None,
            entity_id=str(entity_id)[:100] if entity_id is not None else None,
            description=str(description or '')[:AuditService.MAX_DESCRIPTION_LENGTH],
            details=(details_value[:AuditService.MAX_DETAILS_LENGTH] if details_value else None),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        db.session.add(audit_entry)
        if commit:
            db.session.commit()
        return audit_entry
