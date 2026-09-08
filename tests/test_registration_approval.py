from app.extensions import db
from app.models.auth import User, PASSWORD_ITERATIONS, PASSWORD_SALT_BYTES


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
    return client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)


def test_registration_creates_pending_inactive_user(client, app):
    response = _register(client)
    assert response.status_code == 200
    assert b'pending administrator approval' in response.data

    with app.app_context():
        user = User.query.filter_by(username='newuser').one()
        assert user.approval_status == User.APPROVAL_PENDING
        assert user.is_active is False
        assert user.requested_at is not None
        assert user.password_hash.startswith(f'pbkdf2_sha256${PASSWORD_ITERATIONS}$')
        assert len(user.password_hash.split('$')) == 4
        assert user.check_password('StrongPass123')
        assert user.check_password('WrongPassword') is False
        assert [role.name for role in user.roles] == ['Volunteer']
        assert user.has_permission('dashboard.view') is True


def test_each_password_gets_a_unique_random_salt(app):
    first = User(username='salt1', email='salt1@example.com', full_name='Salt One')
    second = User(username='salt2', email='salt2@example.com', full_name='Salt Two')
    first.set_password('SamePassword123')
    second.set_password('SamePassword123')

    assert first.password_hash != second.password_hash
    first_salt = first.password_hash.split('$')[2]
    second_salt = second.password_hash.split('$')[2]
    assert first_salt != second_salt
    assert len(first_salt) >= 40
    assert len(second_salt) >= 40
    assert PASSWORD_SALT_BYTES == 32
    assert PASSWORD_ITERATIONS == 600_000
    assert first.check_password('SamePassword123')
    assert second.check_password('SamePassword123')


def test_pending_user_cannot_login(client, app):
    _register(client)
    response = _login(client, 'newuser', 'StrongPass123')
    assert response.status_code == 200
    assert b'pending administrator approval' in response.data


def test_admin_can_approve_registration(client, app):
    _register(client)
    _login(client, 'admin', 'password')
    with app.app_context():
        user_id = User.query.filter_by(username='newuser').one().id

    response = client.post(f'/admin/users/{user_id}/approve', follow_redirects=True)
    assert response.status_code == 200
    assert b'has been approved and can now log in' in response.data

    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.approval_status == User.APPROVAL_APPROVED
        assert user.is_active is True
        assert user.approved_by_id is not None
        assert user.reviewed_at is not None
        assert [role.name for role in user.roles] == ['Volunteer']
        assert user.has_permission('dashboard.view') is True

    # GET /auth/logout intentionally renders a CSRF-protected POST form; it
    # does not mutate the session. Use the real POST logout before testing
    # the newly approved user's login.
    client.post('/auth/logout', follow_redirects=True)
    response = _login(client, 'newuser', 'StrongPass123')
    assert response.status_code == 200


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

    # GET /auth/logout intentionally renders a CSRF-protected POST form; it
    # does not mutate the session. Use the real POST logout before checking
    # the rejected account's login response.
    client.post('/auth/logout', follow_redirects=True)
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
