from app.models.auth import User
from app.models.privacy import ConsentRecord, PrivacyRequest
from app.models.income import Donation
from app.models.ledger import Transaction
from app.models.audit import AuditLog
from app.models.mandal import Event
from app.models.ledger import Account
from app.services.donation_service import DonationService


def login(client, username='volunteer', password='password'):
    return client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=True)


def test_privacy_notice_is_public(client):
    response = client.get('/privacy/notice')
    assert response.status_code == 200
    assert b'Privacy Notice' in response.data
    assert b'password hash' in response.data


def test_privacy_center_requires_authentication(client):
    response = client.get('/privacy/', follow_redirects=False)
    assert response.status_code in (302, 401)


def test_authenticated_user_can_submit_privacy_request(client, app):
    login(client)
    response = client.post('/privacy/', data={'request_type': 'ACCESS', 'details': 'Please provide my account data.'}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        item = PrivacyRequest.query.filter_by(request_type='ACCESS').one()
        assert item.status == 'REQUESTED'
        assert item.user_id is not None


def test_optional_consent_requires_explicit_affirmative_confirmation(client, app):
    login(client)
    response = client.post('/privacy/consent', data={
        'purpose': 'analytics', 'action': 'GRANT'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'explicitly confirm' in response.data
    with app.app_context():
        assert ConsentRecord.query.filter_by(purpose='analytics').count() == 0

    response = client.post('/privacy/consent', data={
        'purpose': 'analytics', 'action': 'GRANT', 'consent_confirm': 'yes'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        record = ConsentRecord.query.filter_by(purpose='analytics').one()
        assert record.status == 'GRANTED'
        assert record.notice_version == '1.0'
        assert record.source == 'web'
        assert record.granted_at is not None


def test_authenticated_user_can_grant_and_withdraw_optional_consent(client, app):
    login(client)
    response = client.post('/privacy/consent', data={
        'purpose': 'communications', 'action': 'GRANT', 'consent_confirm': 'yes'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        record = ConsentRecord.query.filter_by(purpose='communications').one()
        assert record.status == 'GRANTED'
    response = client.post('/privacy/consent', data={
        'purpose': 'communications', 'action': 'WITHDRAW'
    }, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        record = ConsentRecord.query.filter_by(purpose='communications').one()
        assert record.status == 'WITHDRAWN'
        assert record.withdrawn_at is not None


def test_invalid_consent_purpose_is_rejected(client, app):
    login(client)
    response = client.post('/privacy/consent', data={
        'purpose': 'financial_processing', 'action': 'GRANT', 'consent_confirm': 'yes'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid consent request' in response.data
    with app.app_context():
        assert ConsentRecord.query.filter_by(purpose='financial_processing').count() == 0


def test_profile_correction_cannot_take_another_users_email(client, app):
    login(client)
    response = client.post('/privacy/profile/correction', data={
        'full_name': 'Changed Name', 'email': 'admin@test.com', 'phone': '9999999999'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'already in use' in response.data
    with app.app_context():
        user = User.query.filter_by(username='volunteer').one()
        assert user.email == 'vol@test.com'


def test_donation_minimises_unnecessary_personal_data(app):
    with app.app_context():
        user = User.query.filter_by(username='volunteer').one()
        event = Event.query.first()
        account = Account.query.first()
        donor_name = 'Minimisation Test Donor'

        donation = DonationService.record_offline_donation(
            event_id=event.id,
            donor_name=donor_name,
            amount='100.00',
            payment_mode='CASH',
            account_id=account.id,
            created_by_id=user.id,
            donor_phone='9999999999',
            donor_email='unnecessary@example.com',
            donor_address='Unnecessary private address',
            pan_number='ABCDE1234F',
            purpose='General Donation',
            notes='Operational note only',
        )

        assert donation.donor_name == donor_name
        assert donation.donor_phone == '9999999999'
        assert donation.donor_email is None
        assert donation.donor_address is None
        assert donation.pan_number is None

        ledger_entry = Transaction.query.filter_by(source_module='DONATION', source_id=donation.id).one()
        assert donor_name not in ledger_entry.description

        audit_entry = AuditLog.query.filter_by(entity_type='DONATION', entity_id=str(donation.id)).one()
        assert donor_name not in audit_entry.description
