"""Ensure the application RBAC catalog and baseline system roles exist.

Application routes enforce permission names that must exist in the permissions
table so administrators can assign them through the Role Editor. The
registration workflow also depends on the Volunteer role being present.
This migration is additive and never removes existing role permissions.
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

ROLE_BASELINES = {
    'Volunteer': [
        'dashboard.view', 'donation.view', 'donation.create',
        'expense.view', 'expense.create', 'document.view', 'document.upload',
    ],
    'Treasurer': [
        'dashboard.view', 'donation.view', 'donation.create', 'donation.receipt',
        'expense.view', 'expense.approve', 'expense.reject', 'expense.pay',
        'vendor.view', 'budget.view', 'document.view', 'document.upload',
        'document.download', 'document.verify', 'report.view', 'report.export',
        'finance.view', 'finance.manage',
    ],
}


def upgrade():
    bind = op.get_bind()
    permissions = sa.table(
        'permissions',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String(100)),
        sa.column('description', sa.String(255)),
        sa.column('module', sa.String(50)),
    )
    roles = sa.table(
        'roles',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String(64)),
        sa.column('description', sa.String(255)),
        sa.column('is_system', sa.Boolean),
    )
    role_permissions = sa.table(
        'role_permissions',
        sa.column('role_id', sa.Integer),
        sa.column('permission_id', sa.Integer),
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

    for role_name, permission_names in ROLE_BASELINES.items():
        role_row = bind.execute(
            sa.select(roles.c.id).where(roles.c.name == role_name)
        ).first()
        if role_row is None:
            bind.execute(
                roles.insert().values(
                    name=role_name,
                    description=(
                        'Record donations and submit expenses'
                        if role_name == 'Volunteer'
                        else 'Financial approval and disbursal role'
                    ),
                    is_system=True,
                )
            )
            role_row = bind.execute(
                sa.select(roles.c.id).where(roles.c.name == role_name)
            ).first()

        for permission_name in permission_names:
            permission_row = bind.execute(
                sa.select(permissions.c.id).where(permissions.c.name == permission_name)
            ).first()
            pair_exists = bind.execute(
                sa.select(sa.literal(1)).select_from(role_permissions).where(
                    role_permissions.c.role_id == role_row.id,
                    role_permissions.c.permission_id == permission_row.id,
                )
            ).first()
            if pair_exists is None:
                bind.execute(
                    role_permissions.insert().values(
                        role_id=role_row.id,
                        permission_id=permission_row.id,
                    )
                )


def downgrade():
    # Permissions and system-role assignments are authorization master data.
    # Never delete or revoke them automatically during rollback.
    pass
