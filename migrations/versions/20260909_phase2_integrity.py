"""Add Phase 2 payment and webhook integrity constraints."""
from alembic import op
import sqlalchemy as sa

revision = '20260909_phase2_integrity'
down_revision = '20260908_contribution_payments'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'donations' in inspector.get_table_names():
        indexes = {idx['name'] for idx in inspector.get_indexes('donations')}
        if 'uq_donations_gateway_order_id' not in indexes:
            op.create_index('uq_donations_gateway_order_id', 'donations', ['gateway_order_id'], unique=True)

    if 'webhook_events' not in inspector.get_table_names():
        op.create_table(
            'webhook_events',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('provider', sa.String(40), nullable=False),
            sa.Column('event_id', sa.String(120), nullable=False),
            sa.Column('event_type', sa.String(100), nullable=False),
            sa.Column('received_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('provider', 'event_id', name='uq_webhook_events_provider_event'),
        )
        op.create_index('ix_webhook_events_provider_type', 'webhook_events', ['provider', 'event_type'])


def downgrade():
    # Financial/webhook idempotency controls are intentionally retained.
    pass
