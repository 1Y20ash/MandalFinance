from app.models.auth import User


def test_user_registration_flow(client, app):
    # Test registration page renders
    res = client.get('/auth/register')
    assert res.status_code == 200
    assert b'Mandal Member Registration' in res.data

    # Test registering a new user
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
