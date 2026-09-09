from app.extensions import db
from app.models.auth import User, Role, Permission
from app.models.audit import AuditLog


def _login(client, username, password='password'):
    return client.post('/auth/login', data={'username': username, 'password': password}, follow_redirects=False)


def test_rbac_permission_checks(app):
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        volunteer = User.query.filter_by(username='volunteer').first()
        assert admin.has_permission('expense.approve') is True
        assert volunteer.has_permission('expense.create') is True
        assert volunteer.has_permission('user.manage') is False


def test_admin_routes_are_server_side_protected(client):
    response = _login(client, 'volunteer')
    assert response.status_code == 302
    for path in ('/admin/users', '/admin/roles', '/admin/audit-logs'):
        assert client.get(path).status_code == 403


def test_finance_control_writes_do_not_inherit_expense_or_donation_create(client):
    assert _login(client, 'volunteer').status_code == 302
    response = client.post('/finance-controls/sponsorships', json={'event_id': 1, 'sponsor_name': 'Unauthorized Sponsor', 'committed_amount': '1000.00'})
    assert response.status_code == 403
    response = client.post('/finance-controls/members', json={'event_id': 1, 'member_name': 'Unauthorized Member', 'target_amount': '1000.00'})
    assert response.status_code == 403
    response = client.post('/finance-controls/reconciliations', json={'account_id': 1, 'statement_date': '2026-09-08', 'statement_balance': '10000.00'})
    assert response.status_code == 403


def test_finance_view_and_manage_permissions_are_distinct(client, app):
    with app.app_context():
        volunteer = User.query.filter_by(username='volunteer').first()
        finance_view = Permission.query.filter_by(name='finance.view').first()
        finance_view_role = Role(name='Finance Viewer')
        finance_view_role.permissions = [finance_view]
        db.session.add(finance_view_role)
        db.session.commit()
        volunteer.roles = [finance_view_role]
        db.session.commit()

    assert _login(client, 'volunteer').status_code == 302
    assert client.get('/finance-controls/events').status_code == 200
    assert client.post('/finance-controls/members', json={'event_id': 1, 'member_name': 'Viewer Must Not Write', 'target_amount': '1000.00'}).status_code == 403

    with app.app_context():
        volunteer = User.query.filter_by(username='volunteer').first()
        finance_view = Permission.query.filter_by(name='finance.view').first()
        finance_manage = Permission.query.filter_by(name='finance.manage').first()
        manage_role = Role(name='Finance Manager')
        manage_role.permissions = [finance_view, finance_manage]
        db.session.add(manage_role)
        db.session.flush()
        volunteer.roles = [manage_role]
        db.session.commit()

    response = client.post('/finance-controls/members', json={'event_id': 1, 'member_name': 'Authorized Member', 'target_amount': '1000.00'})
    assert response.status_code == 201


def test_inactive_user_cannot_login(client, app):
    with app.app_context():
        volunteer = User.query.filter_by(username='volunteer').first()
        volunteer.is_active = False
        db.session.commit()
    response = _login(client, 'volunteer')
    assert response.status_code == 200
    assert b'Invalid username or password.' in response.data
    assert b'deactivated' not in response.data.lower()


def test_system_roles_cannot_be_modified_or_deleted(client, app):
    _login(client, 'admin')
    with app.app_context():
        role = Role.query.filter_by(name='Super Admin').first()
        role_id = role.id
    response = client.post(f'/admin/roles/{role_id}/edit', data={'name': 'Renamed System Role', 'description': 'must not change'})
    assert response.status_code == 302
    response = client.post(f'/admin/roles/{role_id}/delete')
    assert response.status_code == 302
    with app.app_context():
        role = db.session.get(Role, role_id)
        assert role is not None
        assert role.name == 'Super Admin'


def test_role_changes_are_audited(client, app):
    _login(client, 'admin')
    with app.app_context():
        volunteer = User.query.filter_by(username='volunteer').first()
        target_role = Role.query.filter_by(name='Volunteer').first()
        volunteer_id = volunteer.id
        target_role_id = target_role.id
    response = client.post(f'/admin/users/{volunteer_id}/roles', data={'role_ids': [target_role_id]})
    assert response.status_code == 302
    with app.app_context():
        audit = AuditLog.query.filter_by(action='ROLE_CHANGE', entity_type='USER', entity_id=str(volunteer_id)).order_by(AuditLog.created_at.desc()).first()
        assert audit is not None
        assert 'Volunteer' in audit.description


def test_permission_denial_is_server_side_and_audited(client, app):
    _login(client, 'volunteer')
    response = client.get('/admin/roles')
    assert response.status_code == 403
    with app.app_context():
        volunteer = User.query.filter_by(username='volunteer').first()
        audit = AuditLog.query.filter_by(
            action='ADMIN_AUTHORIZATION_DENIED', entity_type='AUTHORIZATION', entity_id=str(volunteer.id)
        ).order_by(AuditLog.created_at.desc()).first()
        assert audit is not None
        assert '/admin/roles' in (audit.details or '') or '/admin/roles' in audit.description


def test_ineligible_authenticated_user_cannot_retain_permission(client, app):
    _login(client, 'volunteer')

    # Strong session protection intentionally rejects a request when the client
    # fingerprint changes. Preserve the legitimate session binding here so this
    # test isolates server-side account eligibility and RBAC authorization.
    with client.session_transaction() as session:
        session_identifier = session.get('_id')
        assert session.get('_user_id') is not None
        assert session_identifier

    with app.app_context():
        volunteer = User.query.filter_by(username='volunteer').first()
        volunteer.is_active = False
        db.session.commit()

    with client.session_transaction() as session:
        session['_id'] = session_identifier

    response = client.get('/dashboard/')
    assert response.status_code == 403


def test_strong_session_protection_rejects_changed_client_identity(client):
    assert _login(client, 'volunteer').status_code == 302
    response = client.get('/dashboard/', headers={'User-Agent': 'MandalFinance-Test-Attacker/1.0'})
    assert response.status_code == 302
