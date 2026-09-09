"""Add durable idempotency records for payment webhooks.

The application can bootstrap metadata in some environments before Alembic
runs. Therefore this migration is intentionally idempotent at the table
boundary: if the exact table already exists, Alembic records the revision
without attempting a duplicate CREATE TABLE.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260909_payment_event'
down_revision = '20260909_income_link'
branch_labels = None
depends_on = None


TABLE_NAME = 'payment_webhook_events'


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABLE_NAME in inspector.get_table_names():
        return

    op.create_table(
        TABLE_NAME,
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(length=100), nullable=False),
        sa.Column('event_type', sa.String(length=80), nullable=False),
        sa.Column('order_id', sa.String(length=100), nullable=True),
        sa.Column('payment_id', sa.String(length=100), nullable=True),
        sa.Column('donation_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PROCESSED'),
        sa.Column('processed_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('PROCESSED', 'IGNORED')",
            name='ck_payment_webhook_events_status',
        ),
        sa.ForeignKeyConstraint(['donation_id'], ['donations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', name='uq_payment_webhook_events_event_id'),
    )
    op.create_index('ix_payment_webhook_events_event_id', TABLE_NAME, ['event_id'], unique=True)
    op.create_index('ix_payment_webhook_events_order_id', TABLE_NAME, ['order_id'], unique=False)
    op.create_index('ix_payment_webhook_events_payment_id', TABLE_NAME, ['payment_id'], unique=False)
    op.create_index('ix_payment_webhook_events_donation_id', TABLE_NAME, ['donation_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if TABLE_NAME not in sa.inspect(bind).get_table_names():
        return

    for index_name in (
        'ix_payment_webhook_events_donation_id',
        'ix_payment_webhook_events_payment_id',
        'ix_payment_webhook_events_order_id',
        'ix_payment_webhook_events_event_id',
    ):
        if any(index.get('name') == index_name for index in sa.inspect(bind).get_indexes(TABLE_NAME)):
            op.drop_index(index_name, table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
