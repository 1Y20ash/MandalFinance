from datetime import datetime, timedelta

from sqlalchemy import or_

from app.extensions import db
from app.models.audit import AuditLog


class RetentionService:
    """Apply bounded retention to operational audit records.

    Financial evidence is retained longer than security/session telemetry. Exact
    periods are configurable and should be aligned with the Mandal's legal and
    accounting retention obligations before production use.
    """

    FINANCIAL_ENTITIES = {'DONATION', 'EXPENSE', 'TRANSACTION', 'SPONSORSHIP', 'MEMBER_CONTRIBUTION', 'RECONCILIATION'}
    FINANCIAL_ACTIONS = {'CREATE', 'UPDATE', 'APPROVE', 'REJECT', 'PAY', 'REVERSE', 'VERIFY', 'EXPORT'}

    @staticmethod
    def purge_audit_logs(financial_days=2555, security_days=180):
        now = datetime.utcnow()
        financial_cutoff = now - timedelta(days=financial_days)
        security_cutoff = now - timedelta(days=security_days)

        financial_query = AuditLog.query.filter(
            AuditLog.created_at < financial_cutoff,
            or_(AuditLog.entity_type.in_(RetentionService.FINANCIAL_ENTITIES),
                AuditLog.action.in_(RetentionService.FINANCIAL_ACTIONS)),
        )
        security_query = AuditLog.query.filter(
            AuditLog.created_at < security_cutoff,
            ~or_(AuditLog.entity_type.in_(RetentionService.FINANCIAL_ENTITIES),
                 AuditLog.action.in_(RetentionService.FINANCIAL_ACTIONS)),
        )

        financial_deleted = financial_query.delete(synchronize_session=False)
        security_deleted = security_query.delete(synchronize_session=False)
        db.session.commit()
        return {
            'financial_deleted': financial_deleted,
            'security_deleted': security_deleted,
            'total_deleted': financial_deleted + security_deleted,
        }
