from app.models.auth import User

def test_rbac_permission_checks(app):
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        volunteer = User.query.filter_by(username='volunteer').first()

        assert admin.has_permission('expense.approve') is True
        assert volunteer.has_permission('expense.create') is True
        assert volunteer.has_permission('user.manage') is False
