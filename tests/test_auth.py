from app.models.auth import User
from app.extensions import db


def login(client, username='volunteer', password='password'):
    return client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)


def test_user_registration_flow(client, app):
    res = client.get('/auth/register')
    assert res.status_code == 200
    assert b'Mandal Member Registration' in res.data

    post_res = client.post('/auth/register', data={
        'full_name': 'Ramesh Kumar',
        'username': 'ramesh_k',
        'email': 'ramesh@test.com',
        'phone': '9876543210',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)

    assert post_res.status_code == 200
    assert b'Registration submitted successfully' in post_res.data
    assert b'pending administrator approval' in post_res.data

    with app.app_context():
        u = User.query.filter_by(username='ramesh_k').first()
        assert u is not None
        assert u.email == 'ramesh@test.com'
        assert u.approval_status == User.APPROVAL_PENDING
        assert u.is_active is False
        assert u.check_password('password123') is True


def test_login_does_not_disclose_account_state(client, app):
    with app.app_context():
        pending = User(
            username='pending_user', email='pending@test.com', full_name='Pending User',
            is_active=False, approval_status=User.APPROVAL_PENDING,
        )
        pending.set_password('password')
        db.session.add(pending)
        db.session.commit()

    pending_res = client.post('/auth/login', data={'username': 'pending_user', 'password': 'password'})
    missing_res = client.post('/auth/login', data={'username': 'does-not-exist', 'password': 'password'})
    assert pending_res.status_code == 200
    assert missing_res.status_code == 200
    assert b'Invalid username or password.' in pending_res.data
    assert b'pending administrator approval' not in pending_res.data
    assert b'Invalid username or password.' in missing_res.data


def test_password_change_requires_current_password_and_invalidates_session(client, app):
    login(client)
    assert client.get('/auth/profile').status_code == 200

    bad = client.post('/auth/password/change', data={
        'current_password': 'wrong-password',
        'new_password': 'new-password-123',
        'confirm_password': 'new-password-123',
    }, follow_redirects=True)
    assert bad.status_code == 200
    assert b'current password is incorrect' in bad.data
    assert client.get('/auth/profile').status_code == 200

    changed = client.post('/auth/password/change', data={
        'current_password': 'password',
        'new_password': 'new-password-123',
        'confirm_password': 'new-password-123',
    }, follow_redirects=True)
    assert changed.status_code == 200
    assert b'Password changed successfully' in changed.data

    # The old session must no longer authorize protected pages.
    assert client.get('/dashboard/').status_code in (302, 303)

    with app.app_context():
        user = User.query.filter_by(username='volunteer').one()
        assert user.check_password('new-password-123') is True
        assert user.check_password('password') is False


def test_authentication_session_configuration(app):
    assert app.login_manager.session_protection == 'strong'
    assert app.config['SESSION_COOKIE_HTTPONLY'] is True
    assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'
    assert app.config['REMEMBER_COOKIE_HTTPONLY'] is True
    assert app.config['REMEMBER_COOKIE_SAMESITE'] == 'Lax'
