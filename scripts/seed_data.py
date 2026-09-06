import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, datetime
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models.auth import User, Role, Permission
from app.models.mandal import Mandal, FinancialYear, Event
from app.models.ledger import Account, TransactionCategory
from app.models.expense import ExpenseCategory

def seed():
    app = create_app('development')
    with app.app_context():
        db.create_all()
        print("Initializing database tables...")

        # 1. Permissions list
        perm_names = [
            ('dashboard.view', 'View financial dashboard', 'dashboard'),
            ('donation.view', 'View donations history', 'donation'),
            ('donation.create', 'Record offline donations', 'donation'),
            ('donation.receipt', 'Download donation receipts', 'donation'),
            ('income.view', 'View income records', 'income'),
            ('income.create', 'Add income entries', 'income'),
            ('expense.view', 'View expense list and details', 'expense'),
            ('expense.create', 'Submit new expense', 'expense'),
            ('expense.approve', 'Approve/reject submitted expenses', 'expense'),
            ('expense.reject', 'Reject submitted expenses', 'expense'),
            ('expense.pay', 'Disburse payment for approved expenses', 'expense'),
            ('vendor.view', 'View vendor list', 'vendor'),
            ('vendor.create', 'Add new vendors', 'vendor'),
            ('vendor.edit', 'Modify vendor details', 'vendor'),
            ('budget.view', 'View budget and limits', 'budget'),
            ('budget.edit', 'Configure budget allocations', 'budget'),
            ('document.view', 'View evidence vault documents', 'document'),
            ('document.upload', 'Upload financial proof documents', 'document'),
            ('document.download', 'Download financial documents', 'document'),
            ('document.replace', 'Replace document (create version N+1)', 'document'),
            ('document.verify', 'Verify SHA-256 digital integrity', 'document'),
            ('evidence_pack.create', 'Generate ZIP evidence pack', 'document'),
            ('report.view', 'View financial reports', 'report'),
            ('report.export', 'Export reports to CSV/PDF', 'report'),
            ('audit_log.view', 'View audit log trail', 'admin'),
            ('user.manage', 'Manage users and roles', 'admin'),
            ('role.manage', 'Manage roles and permissions', 'admin')
        ]

        perms_dict = {}
        for p_name, p_desc, p_mod in perm_names:
            perm = Permission.query.filter_by(name=p_name).first()
            if not perm:
                perm = Permission(name=p_name, description=p_desc, module=p_mod)
                db.session.add(perm)
            perms_dict[p_name] = perm
        db.session.commit()

        # 2. Roles
        admin_role = Role.query.filter_by(name='Super Admin').first()
        if not admin_role:
            admin_role = Role(name='Super Admin', description='Full system access', is_system=True)
            admin_role.permissions = list(Permission.query.all())
            db.session.add(admin_role)

        treasurer_role = Role.query.filter_by(name='Treasurer').first()
        if not treasurer_role:
            treasurer_role = Role(name='Treasurer', description='Financial approval and disbursal role', is_system=True)
            treasurer_role.permissions = [
                perms_dict['dashboard.view'], perms_dict['donation.view'], perms_dict['donation.create'],
                perms_dict['donation.receipt'], perms_dict['expense.view'], perms_dict['expense.approve'],
                perms_dict['expense.reject'], perms_dict['expense.pay'], perms_dict['vendor.view'],
                perms_dict['budget.view'], perms_dict['document.view'], perms_dict['document.upload'],
                perms_dict['document.download'], perms_dict['document.verify'], perms_dict['report.view'],
                perms_dict['report.export']
            ]
            db.session.add(treasurer_role)

        volunteer_role = Role.query.filter_by(name='Volunteer').first()
        if not volunteer_role:
            volunteer_role = Role(name='Volunteer', description='Record donations and submit expenses', is_system=True)
            volunteer_role.permissions = [
                perms_dict['dashboard.view'], perms_dict['donation.view'], perms_dict['donation.create'],
                perms_dict['expense.view'], perms_dict['expense.create'], perms_dict['document.view'],
                perms_dict['document.upload']
            ]
            db.session.add(volunteer_role)

        db.session.commit()

        # 3. Super Admin User
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@ashtavinayak.org',
                full_name='Mandal Administrator',
                is_admin=True,
                is_active=True
            )
            admin_user.set_password('AdminPass2026!')
            admin_user.roles.append(admin_role)
            db.session.add(admin_user)
            db.session.commit()

        # 4. Mandal, Financial Year & Event
        mandal = Mandal.query.first()
        if not mandal:
            mandal = Mandal(
                name='Shree Ashtavinayak Ganesh Utsav Mandal',
                location='Panchasheel Nagar, Gittikhadan, Nagpur, Maharashtra, India',
                contact_phone='+91-9876543210',
                contact_email='info@ashtavinayak.org'
            )
            db.session.add(mandal)
            db.session.commit()

        fy = FinancialYear.query.filter_by(name='FY 2026-2027').first()
        if not fy:
            fy = FinancialYear(
                name='FY 2026-2027',
                start_date=date(2026, 4, 1),
                end_date=date(2027, 3, 31),
                opening_balance=Decimal('25000.00'),
                is_active=True
            )
            db.session.add(fy)
            db.session.commit()

        event = Event.query.filter_by(title='Ganesh Utsav 2026').first()
        if not event:
            event = Event(
                mandal_id=mandal.id,
                financial_year_id=fy.id,
                title='Ganesh Utsav 2026',
                year=2026,
                start_date=date(2026, 9, 1),
                end_date=date(2026, 9, 12),
                budget_target=Decimal('500000.00'),
                is_active=True
            )
            db.session.add(event)
            db.session.commit()

        # 5. Accounts
        accounts_data = [
            ('Main Cash Box', 'cash', Decimal('15000.00')),
            ('State Bank of India (SBI)', 'bank', Decimal('10000.00')),
            ('Mandal UPI Account', 'upi', Decimal('0.00'))
        ]
        for acc_name, acc_type, op_bal in accounts_data:
            if not Account.query.filter_by(name=acc_name).first():
                acc = Account(
                    name=acc_name,
                    account_type=acc_type,
                    opening_balance=op_bal,
                    current_balance=op_bal
                )
                db.session.add(acc)
        db.session.commit()

        # 6. Categories
        tx_cats = [
            ('Donations', 'income'),
            ('Sponsorships', 'income'),
            ('Member Contributions', 'income'),
            ('Other Income', 'income'),
            ('Festival Expenses', 'expense')
        ]
        for cname, ctype in tx_cats:
            if not TransactionCategory.query.filter_by(name=cname, category_type=ctype).first():
                db.session.add(TransactionCategory(name=cname, category_type=ctype))

        exp_cats = [
            'Ganesh Idol', 'Mandap/Pandal', 'Decoration', 'Lighting', 'Sound System',
            'Cultural Programs', 'Prasad', 'Puja Materials', 'Security', 'Cleaning',
            'Advertising', 'Printing', 'Transportation', 'Visarjan', 'Permissions', 'Miscellaneous'
        ]
        for ec in exp_cats:
            if not ExpenseCategory.query.filter_by(name=ec).first():
                db.session.add(ExpenseCategory(name=ec))

        db.session.commit()
        print("Database seeded successfully with initial RBAC, accounts, and categories!")

if __name__ == '__main__':
    seed()
