"""Ensure the application RBAC permission catalog exists in production.

The application routes enforce permissions that must also exist in the
permissions table so administrators can assign them through the Role Editor.
This migration is additive and does not change any existing role assignments.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260917_rbac_permission_catalog'
down_revision = '20260917_account_seeds'
branch_labels = None
depends_on = None


PERMISSIONS = [
    ('dashboard.view', 'View financial dashboard', 'dashboard'),
    ('donation.view', 'View donations history', 'donation'),
    ('donation.create', 'Record offline donations', 'donation'),
    ('donation.receipt', 'Download donation receipts', 'donation'),
    ('income.view', 'View income records', 'income'),
    ('income.create', 'Add income entries', 'income'),
    ('expense.view', 'View expense list and details', 'expense'),
    ('expense.create', 'Submit new expense', 'expense'),
    ('expense.approve', 'Approve submitted expenses', 'expense'),
    ('expense.reject', 'Reject submitted expenses', 'expense'),
    ('expense.pay', 'Disburse payment for approved expenses', 'expense'),
    ('vendor.view', 'View vendor list', 'vendor'),
    ('vendor.create', 'Add new vendors', 'vendor'),
    ('vendor.edit', 'Modify vendor details', 'vendor'),
    ('budget.view', 'View budget and limits', 'budget'),
    ('budget.edit', 'Configure budget allocations', 'budget'),
    ('budget.approve', 'Approve or reject event budgets', 'budget'),
    ('document.view', 'View evidence vault documents', 'document'),
    ('document.upload', 'Upload financial proof documents', 'document'),
    ('document.download', 'Download financial documents', 'document'),
    ('document.replace', 'Replace document and create a new version', 'document'),
    ('document.verify', 'Verify SHA-256 digital integrity', 'document'),
    ('evidence_pack.create', 'Generate a ZIP evidence pack', 'document'),
    ('report.view', 'View financial reports', 'report'),
    ('report.export', 'Export reports to CSV', 'report'),
    ('finance.view', 'View financial control data and reconciliation status', 'finance'),
    ('finance.manage', 'Create, match, resolve and correct financial control records', 'finance'),
    ('audit_log.view', 'View audit log trail', 'admin'),
    ('user.manage', 'Manage users and roles', 'admin'),
    ('role.manage', 'Manage roles and permissions', 'admin'),
]


def upgrade():
    bind = op.get_bind()
    permissions = sa.table(
        'permissions',
        sa.column('name', sa.String(100)),
        sa.column('description', sa.String(255)),
        sa.column('module', sa.String(50)),
    )

    for name, description, module in PERMISSIONS:
        exists = bind.execute(
            sa.select(sa.literal(1)).select_from(permissions).where(
                permissions.c.name == name
            )
        ).first()
        if exists is None:
            bind.execute(
                permissions.insert().values(
                    name=name,
                    description=description,
                    module=module,
                )
            )


def downgrade():
    # Permission rows may be assigned to roles and are authorization master
    # data. Never delete them automatically during a rollback.
    pass
