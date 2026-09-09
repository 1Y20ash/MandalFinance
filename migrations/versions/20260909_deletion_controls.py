"""Add auditable, approval-gated deletion requests.

Deletion is deliberately separate from retention calculation. Financial and
other legally required records are preserved; the workflow primarily removes
account PII and non-essential operational data after an approved request.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260909_deletion_controls'
down_revision = '20260909_retention_policy'
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    bind = op.get_bind()
    if not _table_exists('deletion_requests'):
        op.create_table(
            'deletion_requests',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('requested_by_id', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('decision_reason', sa.Text(), nullable=True),
            sa.Column('legal_hold', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('legal_hold_reason', sa.Text(), nullable=True),
            sa.Column('requested_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('reviewed_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['requested_by_id'], ['users.id'], ondelete='SET NULL'),
            sa.CheckConstraint(
                "status IN ('PENDING', 'APPROVED', 'REJECTED', 'BLOCKED', 'COMPLETED')",
                name='ck_deletion_requests_status',
            ),
            sa.CheckConstraint(
                "(legal_hold = FALSE) OR (length(trim(coalesce(legal_hold_reason, ''))) > 0)",
                name='ck_deletion_requests_hold_reason',
            ),
        )

    inspector = sa.inspect(bind)
    indexes = {index['name'] for index in inspector.get_indexes('deletion_requests')}
    if 'ix_deletion_requests_user_id' not in indexes:
        op.create_index('ix_deletion_requests_user_id', 'deletion_requests', ['user_id'])
    if 'ix_deletion_requests_status' not in indexes:
        op.create_index('ix_deletion_requests_status', 'deletion_requests', ['status'])


def downgrade() -> None:
    # Deletion history is itself compliance evidence; never erase it implicitly.
    pass
