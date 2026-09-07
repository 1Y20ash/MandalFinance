import pytest
from decimal import Decimal

from app import create_app
from app.extensions import db, limiter
from app.models.auth import User, Role, Permission
from app.models.mandal import Mandal, FinancialYear, Event
from app.models.ledger import Account, TransactionCategory
from app.models.expense import ExpenseCategory


@pytest.fixture
def app(tmp_path):
    app = create_app('testing')

    # Tests must never reuse production/local upload artifacts. Each fixture
    # gets an isolated temporary storage root, and the storage driver continues
    # to forbid overwrites exactly as it does outside tests.
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    app.config['SUPABASE_URL'] = ''
    app.config['SUPABASE_SERVICE_ROLE_KEY'] = ''

    with app.app_context():
        db.create_all()

        # Create basic test permissions
        perm_view = Permission(
            name='dashboard.view',
            module='dashboard'
        )
        perm_exp_app = Permission(
            name='expense.approve',
            module='expense'
        )
        perm_exp_create = Permission(
            name='expense.create',
            module='expense'
        )
        perm_donation_view = Permission(
            name='donation.view',
            module='donation'
        )
        perm_donation_create = Permission(
            name='donation.create',
            module='donation'
        )
        perm_document_view = Permission(
            name='document.view',
            module='document'
        )
        perm_document_upload = Permission(
            name='document.upload',
            module='document'
        )

        # PDP hardening permissions
        perm_finance_view = Permission(
            name='finance.view',
            module='finance'
        )
        perm_finance_manage = Permission(
            name='finance.manage',
            module='finance'
        )
        perm_budget_approve = Permission(
            name='budget.approve',
            module='budget'
        )

        db.session.add_all([
            perm_view,
            perm_exp_app,
            perm_exp_create,
            perm_donation_view,
            perm_donation_create,
            perm_document_view,
            perm_document_upload,
            perm_finance_view,
            perm_finance_manage,
            perm_budget_approve,
        ])
        db.session.commit()

        # Super Admin role
        role_admin = Role(
            name='Super Admin',
            is_system=True
        )
        role_admin.permissions = [
            perm_view,
            perm_exp_app,
            perm_exp_create,
            perm_finance_view,
            perm_finance_manage,
            perm_budget_approve,
        ]

        # Normal user role
        role_user = Role(
            name='User',
            is_system=False
        )
        role_user.permissions = [
            perm_view,
            perm_exp_create,
        ]

        # Registration assigns the Volunteer role.
        # Keep the test fixture aligned with the production seed
        # so an approved registrant has dashboard access.
        role_volunteer = Role(
            name='Volunteer',
            is_system=True
        )
        role_volunteer.permissions = [
            perm_view,
            perm_donation_view,
            perm_donation_create,
            perm_exp_create,
            perm_document_view,
            perm_document_upload,
        ]

        db.session.add_all([
            role_admin,
            role_user,
            role_volunteer,
        ])
        db.session.commit()

        # Create test users
        admin_user = User(
            username='admin',
            email='admin@test.com',
            full_name='Admin Test',
            is_admin=True
        )
        admin_user.set_password('password')
        admin_user.roles.append(role_admin)

        normal_user = User(
            username='volunteer',
            email='vol@test.com',
            full_name='Volunteer Test',
            is_admin=False
        )
        normal_user.set_password('password')
        normal_user.roles.append(role_user)

        db.session.add_all([
            admin_user,
            normal_user,
        ])

        # Create Mandal
        mandal = Mandal(
            name='Shree Ashtavinayak Mandal'
        )
        db.session.add(mandal)
        db.session.commit()

        # Create Financial Year
        fy = FinancialYear(
            name='FY 2026-2027',
            start_date=db.func.current_date(),
            end_date=db.func.current_date(),
            opening_balance=Decimal('10000.00')
        )
        db.session.add(fy)
        db.session.commit()

        # Create Event
        event = Event(
            mandal_id=mandal.id,
            financial_year_id=fy.id,
            title='Ganesh Utsav 2026',
            year=2026,
            start_date=db.func.current_date(),
            end_date=db.func.current_date()
        )
        db.session.add(event)

        # Create Account
        account = Account(
            name='Main Cash',
            account_type='cash',
            opening_balance=Decimal('10000.00'),
            current_balance=Decimal('10000.00')
        )
        db.session.add(account)

        # Create Expense Category
        exp_cat = ExpenseCategory(
            name='Decoration'
        )
        db.session.add(exp_cat)

        # Create Transaction Categories
        tx_cat_inc = TransactionCategory(
            name='Donations',
            category_type='income'
        )
        tx_cat_exp = TransactionCategory(
            name='Festival Expenses',
            category_type='expense'
        )
        db.session.add_all([
            tx_cat_inc,
            tx_cat_exp,
        ])

        db.session.commit()

        yield app

        # Cleanup
        db.session.remove()
        db.drop_all()

        # The rate-limit test intentionally consumes a full login bucket.
        # Its Redis state must not leak into later tests that also
        # authenticate as the shared fixture users.
        # Production rate-limit state is unaffected.
        limiter.limiter.storage.reset()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()
