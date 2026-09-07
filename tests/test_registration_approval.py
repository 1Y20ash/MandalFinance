from app.extensions import db
from app.models.auth import User


def _register(client, username='newuser', email='new@example.com', password='StrongPass123'):
    return client.post('/auth/register', data={
        'full_name': 'New Mandal Member',
        'username': username,
        'email': email,
        'phone': '9876543210',
        'password': password,
        'confirm_password': password,
    }, follow_redirects=True)


def _login(client, username, password):
    return client.post('/auth/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)


def test_registration_creates_pending_inactive_user(client, app):
    response = _register(client)

    assert response.status_code == 200
    assert b'pending administrator approval' in response.data

    with app.app_context():
        user = User.query.filter_by(username='newuser').one()
        assert user.approval_status == User.APPROVAL_PENDING
        assert user.is_active is False
        assert user.requested_at is not None
        assert user.password_hash.startswith('pbkdf2:sha256:600000:')
        assert user.check_password('StrongPass123')
        assert user.check_password('WrongPassword') is False


def test_pending_user_cannot_login(client, app):
    _register(client)
    response = _login(client, 'newuser', 'StrongPass123')

    assert response.status_code == 200
    assert b'pending administrator approval' in response.data

    with app.app_context():
        user = User.query.filter_by(username='newuser').one()
        assert user.approval_status == User.APPROVAL_PENDING


def test_admin_can_approve_registration(client, app):
    _register(client)
    _login(client, 'admin', 'password')

    with app.app_context():
        user = User.query.filter_by(username='newuser').one()
        user_id = user.id

    response = client.post(f'/admin/users/{user_id}/approve', follow_redirects=True)
    assert response.status_code == 200
    assert b'has been approved and can now log in' in response.data

    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.approval_status == User.APPROVAL_APPROVED
        assert user.is_active is True
        assert user.approved_by_id is not None
        assert user.reviewed_at is not None

    response = _login(client, 'newuser', 'StrongPass123')
    assert response.status_code == 200
    assert b'pending administrator approval' not in response.data


def test_admin_can_reject_registration_and_record_reason(client, app):
    _register(client)
    _login(client, 'admin', 'password')

    with app.app_context():
        user_id = User.query.filter_by(username='newuser').one().id

    response = client.post(
        f'/admin/users/{user_id}/reject',
        data={'rejection_reason': 'Registration details require verification.'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b'registration was rejected' in response.data

    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.approval_status == User.APPROVAL_REJECTED
        assert user.is_active is False
        assert user.rejection_reason == 'Registration details require verification.'
        assert user.approved_by_id is not None
        assert user.reviewed_at is not None

    response = _login(client, 'newuser', 'StrongPass123')
    assert response.status_code == 200
    assert b'registration request was rejected' in response.data


def test_duplicate_registration_is_rejected(client, app):
    _register(client)
    response = _register(client, username='another', email='new@example.com')

    assert response.status_code == 200
    assert b'already exists' in response.data

    with app.app_context():
        assert User.query.filter_by(email='new@example.com').count() == 1
