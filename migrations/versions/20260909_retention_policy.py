"""Add explicit, auditable data-retention policy metadata.

The bootstrap migration creates the current SQLAlchemy metadata, so this
revision is intentionally idempotent when the retention model is already
present. It then ensures the policy catalogue contains the required defaults.
Destructive deletion is deliberately deferred to the dedicated deletion phase.
"""

from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = '20260909_retention_policy'
down_revision = '20260909_db_hardening'
branch_labels = None
depends_on = None


DEFAULT_POLICIES = (
    ('FINANCIAL_RECORDS', 3650, 'Internal financial-record retention policy'),
    ('PAYMENT_EVENTS', 730, 'Internal payment-event retention policy'),
    ('DOCUMENT_EVIDENCE', 3650, 'Internal evidence-retention policy'),
    ('AUDIT_LOGS', 3650, 'Internal audit-trail retention policy'),
    ('NOTIFICATIONS', 90, 'Internal operational-notification retention policy'),
    ('USER_ACCOUNTS', 365, 'Internal inactive-account review policy'),
)


def _table_exists(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _table_exists('retention_policies'):
        op.create_table(
            'retention_policies',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('data_category', sa.String(length=80), nullable=False, unique=True),
            sa.Column('retention_days', sa.Integer(), nullable=False),
            sa.Column('retention_basis', sa.String(length=120), nullable=False),
            sa.Column('disposal_action', sa.String(length=20), nullable=False, server_default='REVIEW'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint('retention_days > 0', name='ck_retention_policies_days_positive'),
            sa.CheckConstraint("disposal_action IN ('REVIEW', 'ARCHIVE')", name='ck_retention_policies_action'),
        )

    inspector = sa.inspect(op.get_bind())
    existing_indexes = {index['name'] for index in inspector.get_indexes('retention_policies')}
    if 'ix_retention_policies_data_category' not in existing_indexes:
        op.create_index(
            'ix_retention_policies_data_category',
            'retention_policies',
            ['data_category'],
            unique=False,
        )

    table = sa.table(
        'retention_policies',
        sa.column('data_category', sa.String()),
        sa.column('retention_days', sa.Integer()),
        sa.column('retention_basis', sa.String()),
        sa.column('disposal_action', sa.String()),
        sa.column('is_active', sa.Boolean()),
        sa.column('created_at', sa.DateTime()),
        sa.column('updated_at', sa.DateTime()),
    )
    now = datetime.utcnow()
    bind = op.get_bind()
    for category, days, basis in DEFAULT_POLICIES:
        exists = bind.execute(
            sa.select(sa.literal(1)).select_from(table).where(table.c.data_category == category).limit(1)
        ).scalar()
        if not exists:
            bind.execute(table.insert().values(
                data_category=category,
                retention_days=days,
                retention_basis=basis,
                disposal_action='REVIEW',
                is_active=True,
                created_at=now,
                updated_at=now,
            ))


def downgrade() -> None:
    # Retention metadata is governance evidence. Do not silently remove it on downgrade.
    pass
