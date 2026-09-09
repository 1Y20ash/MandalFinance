"""Add durable idempotency records for payment webhooks."""

from alembic import op
import sqlalchemy as sa

revision = '20260909_payment_event'
down_revision = '20260909_income_link'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'payment_webhook_events',
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
    op.create_index('ix_payment_webhook_events_event_id', 'payment_webhook_events', ['event_id'], unique=True)
    op.create_index('ix_payment_webhook_events_order_id', 'payment_webhook_events', ['order_id'], unique=False)
    op.create_index('ix_payment_webhook_events_payment_id', 'payment_webhook_events', ['payment_id'], unique=False)
    op.create_index('ix_payment_webhook_events_donation_id', 'payment_webhook_events', ['donation_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_payment_webhook_events_donation_id', table_name='payment_webhook_events')
    op.drop_index('ix_payment_webhook_events_payment_id', table_name='payment_webhook_events')
    op.drop_index('ix_payment_webhook_events_order_id', table_name='payment_webhook_events')
    op.drop_index('ix_payment_webhook_events_event_id', table_name='payment_webhook_events')
    op.drop_table('payment_webhook_events')
