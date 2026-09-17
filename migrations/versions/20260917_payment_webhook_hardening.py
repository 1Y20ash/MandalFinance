"""Persist Razorpay webhook idempotency metadata.

Revision ID: 20260917_payment_webhook
Revises: 20260917_merge_upi_into_bank

The 0001 bootstrap creates the schema from SQLAlchemy metadata. When the
metadata already contains these columns, the bootstrap has already created
them before this revision runs. This revision therefore adds only objects
that are genuinely missing, so clean databases and upgraded databases both
follow the same migration path.

The revision identifier is intentionally <= 32 characters because Alembic's
standard version table uses VARCHAR(32).
"""

from alembic import op
import sqlalchemy as sa

revision = '20260917_payment_webhook'
down_revision = '20260917_merge_upi_into_bank'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column['name'] for column in inspector.get_columns('donations')}

    if 'gateway_webhook_event_id' not in columns:
        op.add_column(
            'donations',
            sa.Column('gateway_webhook_event_id', sa.String(length=100), nullable=True),
        )

    if 'gateway_webhook_signature' not in columns:
        op.add_column(
            'donations',
            sa.Column('gateway_webhook_signature', sa.String(length=255), nullable=True),
        )

    inspector = sa.inspect(bind)
    indexes = {index['name'] for index in inspector.get_indexes('donations')}
    if 'ix_donations_gateway_webhook_event_id' not in indexes:
        op.create_index(
            'ix_donations_gateway_webhook_event_id',
            'donations',
            ['gateway_webhook_event_id'],
            unique=True,
        )


def downgrade():
    # Keep the bootstrap schema intact. These objects may have been created by
    # 0001 from SQLAlchemy metadata rather than by this revision itself.
    pass
