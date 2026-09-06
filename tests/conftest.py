import pytest
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models.auth import User, Role, Permission
from app.models.mandal import Mandal, FinancialYear, Event
from app.models.ledger import Account, TransactionCategory
from app.models.expense import ExpenseCategory

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()

        # Create basic test data
        perm_view = Permission(name='dashboard.view', module='dashboard')
        perm_exp_app = Permission(name='expense.approve', module='expense')
        perm_exp_create = Permission(name='expense.create', module='expense')
        db.session.add_all([perm_view, perm_exp_app, perm_exp_create])
        db.session.commit()

        role_admin = Role(name='Super Admin', is_system=True)
        role_admin.permissions = [perm_view, perm_exp_app, perm_exp_create]

        role_user = Role(name='User', is_system=False)
        role_user.permissions = [perm_view, perm_exp_create]
        db.session.add_all([role_admin, role_user])
        db.session.commit()

        admin_user = User(username='admin', email='admin@test.com', full_name='Admin Test', is_admin=True)
        admin_user.set_password('password')
        admin_user.roles.append(role_admin)

        normal_user = User(username='volunteer', email='vol@test.com', full_name='Volunteer Test', is_admin=False)
        normal_user.set_password('password')
        normal_user.roles.append(role_user)

        db.session.add_all([admin_user, normal_user])

        mandal = Mandal(name='Shree Ashtavinayak Mandal')
        db.session.add(mandal)
        db.session.commit()

        fy = FinancialYear(name='FY 2026-2027', start_date=db.func.current_date(), end_date=db.func.current_date(), opening_balance=Decimal('10000.00'))
        db.session.add(fy)
        db.session.commit()

        event = Event(mandal_id=mandal.id, financial_year_id=fy.id, title='Ganesh Utsav 2026', year=2026, start_date=db.func.current_date(), end_date=db.func.current_date())
        db.session.add(event)

        account = Account(name='Main Cash', account_type='cash', opening_balance=Decimal('10000.00'), current_balance=Decimal('10000.00'))
        db.session.add(account)

        exp_cat = ExpenseCategory(name='Decoration')
        db.session.add(exp_cat)

        tx_cat_inc = TransactionCategory(name='Donations', category_type='income')
        tx_cat_exp = TransactionCategory(name='Festival Expenses', category_type='expense')
        db.session.add_all([tx_cat_inc, tx_cat_exp])

        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
