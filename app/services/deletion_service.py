import secrets
from datetime import datetime

from app.extensions import db
from app.models.audit import AuditLog, Notification
from app.models.auth import User
from app.models.deletion import DeletionRequest
from app.services.audit_service import AuditService


class DeletionService:
    """Execute controlled privacy erasure without destroying financial evidence."""

    @staticmethod
    def request_for_user(user, reason=None):
        if user is None or not getattr(user, 'id', None):
            raise ValueError('A valid user is required.')

        existing = DeletionRequest.query.filter(
            DeletionRequest.user_id == user.id,
            DeletionRequest.status.in_(['PENDING', 'APPROVED']),
        ).first()
        if existing:
            raise ValueError('An active deletion request already exists for this account.')

        request = DeletionRequest(
            user_id=user.id,
            requested_by_id=user.id,
            status='PENDING',
            reason=(reason or '').strip()[:5000] or None,
        )
        db.session.add(request)
        AuditService.log_action(
            'REQUEST_DELETION',
            'USER',
            user.id,
            'User submitted a privacy deletion request.',
            user_override=user,
            commit=False,
        )
        db.session.commit()
        return request

    @staticmethod
    def review(request_id, actor, approve, decision_reason=None, legal_hold=False, legal_hold_reason=None):
        request = db.session.get(DeletionRequest, request_id)
        if request is None:
            raise ValueError('Deletion request not found.')
        if request.status != 'PENDING':
            raise ValueError('Only pending deletion requests can be reviewed.')

        reason = (decision_reason or '').strip()[:5000] or None
        hold_reason = (legal_hold_reason or '').strip()[:5000] or None
        if legal_hold and not hold_reason:
            raise ValueError('A legal-hold reason is required.')

        request.reviewed_at = datetime.utcnow()
        request.decision_reason = reason
        request.legal_hold = bool(legal_hold)
        request.legal_hold_reason = hold_reason

        if legal_hold:
            request.status = 'BLOCKED'
            AuditService.log_action(
                'BLOCK_DELETION', 'DELETION_REQUEST', request.id,
                'Deletion request blocked by legal/operational hold.',
                user_override=actor, commit=False,
            )
            db.session.commit()
            return request

        if not approve:
            request.status = 'REJECTED'
            AuditService.log_action(
                'REJECT_DELETION', 'DELETION_REQUEST', request.id,
                'Privacy deletion request rejected after review.',
                user_override=actor, commit=False,
            )
            db.session.commit()
            return request

        request.status = 'APPROVED'
        AuditService.log_action(
            'APPROVE_DELETION', 'DELETION_REQUEST', request.id,
            'Privacy deletion request approved; controlled erasure executed atomically.',
            user_override=actor, commit=False,
        )
        DeletionService._erase_user(request)
        return request

    @staticmethod
    def _erase_user(request):
        user = db.session.get(User, request.user_id) if request.user_id else None
        if user is None:
            request.status = 'COMPLETED'
            request.completed_at = datetime.utcnow()
            db.session.commit()
            return

        # Do not allow the last administrator account to be erased; this is an
        # operational safety control and can be overridden only by a separate
        # governance process, not by the deletion endpoint.
        if user.is_admin:
            other_admin = User.query.filter(
                User.is_admin.is_(True),
                User.is_active.is_(True),
                User.id != user.id,
            ).first()
            if other_admin is None:
                request.status = 'BLOCKED'
                request.legal_hold = True
                request.legal_hold_reason = 'Last active administrator account; manual governance review required.'
                AuditService.log_action(
                    'BLOCK_DELETION', 'DELETION_REQUEST', request.id,
                    'Deletion blocked because the account is the last active administrator.',
                    commit=False,
                )
                db.session.commit()
                return

        # Operational notifications are not financial evidence and can be removed.
        Notification.query.filter_by(user_id=user.id).delete(synchronize_session=False)

        # Preserve financial records, documents, payment events and audit history.
        # Remove account PII while keeping the stable internal row so retained
        # records and foreign keys remain valid and historically traceable.
        original_id = user.id
        user.username = f'deleted-user-{original_id}'[:64]
        user.email = f'deleted-user-{original_id}@invalid.local'[:120]
        user.full_name = 'Deleted User'
        user.phone = None
        user.password_hash = f'disabled${secrets.token_urlsafe(48)}'
        user.is_active = False
        user.is_admin = False
        user.roles = []
        user.approval_status = User.APPROVAL_REJECTED
        user.rejection_reason = 'Account erased under an approved privacy deletion request.'

        # Audit rows retain the event but not the former email address.
        AuditLog.query.filter_by(user_id=original_id).update(
            {AuditLog.user_email: None}, synchronize_session=False
        )

        request.status = 'COMPLETED'
        request.completed_at = datetime.utcnow()
        AuditService.log_action(
            'COMPLETE_DELETION', 'DELETION_REQUEST', request.id,
            'Controlled privacy erasure completed; required financial and compliance evidence retained.',
            commit=False,
        )
        db.session.commit()
