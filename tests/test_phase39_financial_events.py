from datetime import date

from app.extensions import db
from app.models.mandal import Event, FinancialYear


def login_as_admin(client):
    response = client.post('/auth/login', data={'username': 'admin', 'password': 'password'}, follow_redirects=False)
    assert response.status_code in (302, 303)


def test_admin_financial_event_page_requires_admin(client):
    response = client.get('/admin/financial-events', follow_redirects=False)
    assert response.status_code in (302, 303)
    assert '/auth/login' in response.headers['Location']


def test_admin_can_create_and_activate_event(client, app):
    login_as_admin(client)

    with app.app_context():
        fy = FinancialYear.query.filter_by(name='FY 2026-2027').one()
        mandal_id = fy.events[0].mandal_id

    create = client.post('/admin/financial-events/create', data={
        'title': 'Test Operational Event',
        'year': '2026',
        'mandal_id': str(mandal_id),
        'financial_year_id': str(fy.id),
        'start_date': str(date.today()),
        'end_date': str(date.today()),
        'budget_target': '50000.00',
    }, follow_redirects=False)
    assert create.status_code in (302, 303)

    with app.app_context():
        event = Event.query.filter_by(title='Test Operational Event').one()
        assert event.status == 'OPEN'
        assert event.is_active is False
        event_id = event.id

    activate = client.post(f'/admin/financial-events/{event_id}/activate', follow_redirects=False)
    assert activate.status_code in (302, 303)

    with app.app_context():
        event = db.session.get(Event, event_id)
        assert event.status == 'OPEN'
        assert event.is_active is True
        assert Event.query.filter_by(is_active=True).count() == 1


def test_admin_activation_rejects_closed_event(client, app):
    login_as_admin(client)
    with app.app_context():
        event = Event.query.first()
        event.status = 'CLOSED'
        event.is_active = False
        db.session.commit()
        event_id = event.id

    response = client.post(f'/admin/financial-events/{event_id}/activate', follow_redirects=False)
    assert response.status_code in (302, 303)

    with app.app_context():
        event = db.session.get(Event, event_id)
        assert event.status == 'CLOSED'
        assert event.is_active is False
