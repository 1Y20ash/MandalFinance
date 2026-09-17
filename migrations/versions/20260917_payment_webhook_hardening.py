"""Persist Razorpay webhook idempotency metadata.

Revision ID: 20260917_payment_webhook_hardening
Revises: 20260917_merge_upi_into_bank
"""

from alembic import op
import sqlalchemy as sa

revision = '20260917_payment_webhook_hardening'
down_revision = '20260917_merge_upi_into_bank'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('donations', sa.Column('gateway_webhook_event_id', sa.String(length=100), nullable=True))
    op.add_column('donations', sa.Column('gateway_webhook_signature', sa.String(length=255), nullable=True))
    op.create_index(
        'ix_donations_gateway_webhook_event_id',
        'donations',
        ['gateway_webhook_event_id'],
        unique=True,
    )


def downgrade():
    op.drop_index('ix_donations_gateway_webhook_event_id', table_name='donations')
    op.drop_column('donations', 'gateway_webhook_signature')
    op.drop_column('donations', 'gateway_webhook_event_id')
