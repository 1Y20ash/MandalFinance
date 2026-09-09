from app.extensions import db
from app.models.audit import AuditLog, Notification
from app.models.auth import User
from app.models.deletion import DeletionRequest
from app.models.retention import RetentionPolicy
from app.services.deletion_service import DeletionService


def test_user_can_submit_and_cancel_deletion_request(app):
    with app.app_context():
        user = db.session.query(User).filter_by(username='volunteer').one()
        request = DeletionService.request_for_user(user, 'Please erase my account data.')
        assert request.status == 'PENDING'
        assert DeletionRequest.query.count() == 1

        try:
            DeletionService.request_for_user(user)
            assert False, 'duplicate active deletion request was accepted'
        except ValueError as exc:
            assert 'active deletion request' in str(exc)

        request.status = 'REJECTED'
        db.session.commit()
        second = DeletionService.request_for_user(user)
        assert second.status == 'PENDING'


def test_legal_hold_blocks_deletion(app):
    with app.app_context():
        user = db.session.query(User).filter_by(username='volunteer').one()
        request = DeletionService.request_for_user(user)
        reviewed = DeletionService.review(
            request.id,
            db.session.query(User).filter_by(username='admin').one(),
            approve=False,
            legal_hold=True,
            legal_hold_reason='Open audit dispute requires preservation.',
        )
        assert reviewed.status == 'BLOCKED'
        assert reviewed.legal_hold is True
        assert user.is_active is True
        assert user.email == 'vol@test.com'


def test_approved_deletion_anonymizes_account_and_removes_notifications(app):
    with app.app_context():
        user = db.session.query(User).filter_by(username='volunteer').one()
        admin = db.session.query(User).filter_by(username='admin').one()
        db.session.add(Notification(
            user_id=user.id,
            title='Test notification',
            message='Temporary operational message',
            notification_type='INFO',
        ))
        db.session.commit()

        audit = AuditLog(
            user_id=user.id,
            user_email=user.email,
            action='TEST',
            entity_type='USER',
            entity_id=str(user.id),
            description='test audit record',
        )
        db.session.add(audit)
        db.session.commit()

        request = DeletionService.request_for_user(user)
        completed = DeletionService.review(
            request.id,
            admin,
            approve=True,
            decision_reason='Approved after privacy review.',
        )

        assert completed.status == 'COMPLETED'
        assert completed.completed_at is not None
        db.session.refresh(user)
        assert user.username == f'deleted-user-{user.id}'
        assert user.email == f'deleted-user-{user.id}@invalid.local'
        assert user.full_name == 'Deleted User'
        assert user.phone is None
        assert user.is_active is False
        assert user.is_admin is False
        assert user.roles == []
        assert Notification.query.filter_by(user_id=user.id).count() == 0
        db.session.refresh(audit)
        assert audit.user_email is None


def test_last_admin_cannot_be_erased(app):
    with app.app_context():
        admin = db.session.query(User).filter_by(username='admin').one()
        request = DeletionService.request_for_user(admin)
        result = DeletionService.review(
            request.id,
            admin,
            approve=True,
            decision_reason='Attempted self-erasure.',
        )
        assert result.status == 'BLOCKED'
        assert result.legal_hold is True
        assert db.session.get(User, admin.id).is_admin is True


def test_erased_account_is_not_reloaded_into_a_session(app):
    with app.app_context():
        user = db.session.query(User).filter_by(username='volunteer').one()
        user.is_active = False
        db.session.commit()
        with app.test_request_context('/'):
            loaded = app.login_manager._user_callback(str(user.id))
        assert loaded is None


def test_delete_retention_action_is_restricted_to_user_accounts(client, app):
    with app.app_context():
        admin = db.session.query(User).filter_by(username='admin').one()
        policy = RetentionPolicy(
            data_category='FINANCIAL_TEST',
            retention_days=30,
            retention_basis='Test financial policy',
            disposal_action='REVIEW',
        )
        db.session.add(policy)
        db.session.commit()

        with client.session_transaction() as session:
            session['_user_id'] = str(admin.id)
            session['_fresh'] = True
        response = client.post(
            f'/admin/retention/{policy.id}',
            data={'retention_days': '30', 'disposal_action': 'DELETE'},
            follow_redirects=True,
        )
        assert response.status_code == 200
        db.session.refresh(policy)
        assert policy.disposal_action == 'REVIEW'
