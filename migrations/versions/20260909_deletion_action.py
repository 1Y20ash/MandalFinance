"""Permit DELETE as a governed retention disposal action."""

from alembic import op
import sqlalchemy as sa

revision = '20260909_deletion_action'
down_revision = '20260909_deletion_controls'
branch_labels = None
depends_on = None


def _constraint_exists(name: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return False
    return bool(bind.execute(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conname = :name LIMIT 1"
    ), {'name': name}).scalar())


def upgrade() -> None:
    if _constraint_exists('ck_retention_policies_action'):
        op.drop_constraint('ck_retention_policies_action', 'retention_policies', type_='check')
    if op.get_bind().dialect.name == 'postgresql':
        op.create_check_constraint(
            'ck_retention_policies_action',
            'retention_policies',
            "disposal_action IN ('REVIEW', 'ARCHIVE', 'DELETE')",
        )


def downgrade() -> None:
    # Do not weaken an active deletion-control contract during downgrade.
    pass
