from datetime import datetime

from app.extensions import db
from app.models.retention import RetentionPolicy
from app.services.audit_service import AuditService


DEFAULT_RETENTION_POLICIES = {
    'FINANCIAL_RECORDS': (3650, 'Internal financial-record retention policy'),
    'PAYMENT_EVENTS': (730, 'Internal payment-event retention policy'),
    'DOCUMENT_EVIDENCE': (3650, 'Internal evidence-retention policy'),
    'AUDIT_LOGS': (3650, 'Internal audit-trail retention policy'),
    'NOTIFICATIONS': (90, 'Internal operational-notification retention policy'),
    'USER_ACCOUNTS': (365, 'Internal inactive-account review policy'),
}


class RetentionService:
    @staticmethod
    def get_policy(data_category):
        return RetentionPolicy.query.filter_by(
            data_category=data_category.upper(), is_active=True
        ).first()

    @staticmethod
    def expiry_for(data_category, created_at):
        policy = RetentionService.get_policy(data_category)
        if not policy:
            raise ValueError(f'No active retention policy exists for {data_category}.')
        return policy.expires_at(created_at)

    @staticmethod
    def is_due(data_category, created_at, now=None):
        now = now or datetime.utcnow()
        return RetentionService.expiry_for(data_category, created_at) <= now

    @staticmethod
    def seed_defaults(commit=True):
        """Create missing policy rows without overwriting an approved policy."""
        created = []
        for category, (days, basis) in DEFAULT_RETENTION_POLICIES.items():
            policy = RetentionPolicy.query.filter_by(data_category=category).first()
            if policy is None:
                policy = RetentionPolicy(
                    data_category=category,
                    retention_days=days,
                    retention_basis=basis,
                    disposal_action='REVIEW',
                    is_active=True,
                )
                db.session.add(policy)
                created.append(category)
        if commit:
            db.session.commit()
        return created

    @staticmethod
    def record_policy_change(policy, actor=None):
        AuditService.log_action(
            action='UPDATE',
            entity_type='RETENTION_POLICY',
            entity_id=policy.id,
            description=(
                f'Updated retention policy {policy.data_category}: '
                f'{policy.retention_days} days; disposal action {policy.disposal_action}.'
            ),
            user_override=actor,
            commit=False,
        )
