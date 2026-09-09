import hashlib
import json
import uuid
from datetime import datetime

from flask import has_request_context, request
from flask_login import current_user

from app.extensions import db
from app.models.audit import AuditLog


_SENSITIVE_KEYS = {
    'password', 'password_confirmation', 'confirm_password', 'token', 'access_token',
    'refresh_token', 'secret', 'api_key', 'apikey', 'key_secret', 'authorization',
    'cookie', 'session', 'csrf_token', 'webhook_secret', 'service_role_key',
}


class AuditService:
    @staticmethod
    def _redact(value):
        if isinstance(value, dict):
            return {
                str(key): '[REDACTED]' if str(key).lower() in _SENSITIVE_KEYS else AuditService._redact(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [AuditService._redact(item) for item in value]
        return value

    @staticmethod
    def _serialize_details(details):
        if details is None:
            return None
        sanitized = AuditService._redact(details)
        return json.dumps(sanitized, sort_keys=True, separators=(',', ':'), default=str)

    @staticmethod
    def _request_metadata():
        if not has_request_context():
            return None, None, None
        request_id = request.headers.get('X-Request-ID')
        if request_id:
            request_id = request_id[:128]
        ip_address = request.remote_addr
        user_agent = str(request.user_agent)[:250] if request.user_agent else None
        return request_id, ip_address, user_agent

    @staticmethod
    def _canonical_payload(entry):
        return json.dumps({
            'event_id': entry.event_id,
            'user_id': entry.user_id,
            'user_email': entry.user_email,
            'action': entry.action,
            'entity_type': entry.entity_type,
            'entity_id': entry.entity_id,
            'description': entry.description,
            'details': entry.details,
            'outcome': entry.outcome,
            'request_id': entry.request_id,
            'ip_address': entry.ip_address,
            'user_agent': entry.user_agent,
            'created_at': entry.created_at.isoformat() if entry.created_at else None,
        }, sort_keys=True, separators=(',', ':'))

    @staticmethod
    def _integrity_hash(entry):
        return hashlib.sha256(AuditService._canonical_payload(entry).encode('utf-8')).hexdigest()

    @staticmethod
    def log_action(action, entity_type, entity_id=None, description='', details=None,
                   user_override=None, commit=True, outcome='success'):
        """Append an immutable, tamper-evident audit event.

        ``commit=False`` is intended for business transactions that must commit
        the audit event atomically with the state change being recorded.
        """
        if not action or not entity_type or not description:
            raise ValueError('Audit action, entity type and description are required.')

        user_id = None
        user_email = None
        if user_override is not None:
            user_id = user_override.id
            user_email = user_override.email
        elif has_request_context() and current_user.is_authenticated:
            user_id = current_user.id
            user_email = current_user.email

        request_id, ip_address, user_agent = AuditService._request_metadata()
        entry = AuditLog(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            user_email=user_email,
            action=str(action)[:50],
            entity_type=str(entity_type)[:50],
            entity_id=str(entity_id)[:50] if entity_id is not None else None,
            description=str(description),
            details=AuditService._serialize_details(details),
            outcome=str(outcome).lower()[:20],
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            # The digest is non-null in production, so the timestamp must be
            # explicit before INSERT rather than populated by SQLAlchemy later.
            created_at=datetime.utcnow(),
        )
        entry.integrity_hash = AuditService._integrity_hash(entry)
        db.session.add(entry)
        if commit:
            db.session.commit()
        return entry

    @staticmethod
    def verify_integrity(session=None):
        """Recalculate every audit hash and return a diagnostic result."""
        session = session or db.session
        entries = session.query(AuditLog).order_by(AuditLog.id.asc()).all()
        invalid_ids = [
            entry.id for entry in entries
            if not entry.integrity_hash or entry.integrity_hash != AuditService._integrity_hash(entry)
        ]
        return {
            'valid': not invalid_ids,
            'checked': len(entries),
            'invalid_ids': invalid_ids,
        }
