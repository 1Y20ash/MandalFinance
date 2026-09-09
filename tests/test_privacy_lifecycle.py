from app.extensions import db
from app.models.auth import User
from app.models.privacy import ConsentRecord, PrivacyRequest


def login(client, username='volunteer', password='password'):
    return client.post('/login', data={'username': username, 'password': password}, follow_redirects=True)


def test_privacy_notice_is_public(client):
    response = client.get('/privacy/notice')
    assert response.status_code == 200
    assert b'Privacy Notice' in response.data
    assert b'password hashes' in response.data


def test_privacy_center_requires_authentication(client):
    response = client.get('/privacy/', follow_redirects=False)
    assert response.status_code in (302, 401)


def test_authenticated_user_can_submit_privacy_request(client, app):
    login(client)
    response = client.post('/privacy/', data={
        'request_type': 'ACCESS',
        'details': 'Please provide the personal data associated with my account.',
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        item = PrivacyRequest.query.filter_by(request_type='ACCESS').one()
        assert item.status == 'REQUESTED'
        assert item.user_id is not None


def test_authenticated_user_can_grant_and_withdraw_optional_consent(client, app):
    login(client)
    response = client.post('/privacy/consent', data={
        'purpose': 'analytics', 'action': 'GRANT'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        record = ConsentRecord.query.filter_by(purpose='analytics').one()
        assert record.status == 'GRANTED'

    response = client.post('/privacy/consent', data={
        'purpose': 'analytics', 'action': 'WITHDRAW'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        record = ConsentRecord.query.filter_by(purpose='analytics').one()
        assert record.status == 'WITHDRAWN'
        assert record.withdrawn_at is not None


def test_profile_correction_cannot_take_another_users_email(client, app):
    login(client)
    response = client.post('/privacy/profile/correction', data={
        'full_name': 'Changed Name',
        'email': 'admin@test.com',
        'phone': '9999999999',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'already in use' in response.data
    with app.app_context():
        user = User.query.filter_by(username='volunteer').one()
        assert user.email == 'vol@test.com'
