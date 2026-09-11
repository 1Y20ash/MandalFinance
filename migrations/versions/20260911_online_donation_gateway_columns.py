"""Ensure online-donation gateway columns exist on legacy databases.

The bootstrap revision creates the current metadata only for new databases.
Older production databases can therefore reach the online-donation route with
an existing ``donations`` table that predates the gateway columns. The GET
page still works, but the POST fails when SQLAlchemy flushes a Donation using
those missing columns. This migration makes the online-payment schema
explicit and idempotent for both fresh and legacy installations.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260911_online_gateway'
down_revision = '20260911_mandal_bootstrap'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column['name'] for column in inspector.get_columns('donations')}

    additions = [
        ('gateway_order_id', sa.String(length=100)),
        ('gateway_payment_id', sa.String(length=100)),
        ('gateway_signature', sa.String(length=255)),
    ]
    for name, column_type in additions:
        if name not in columns:
            op.add_column(
                'donations',
                sa.Column(name, column_type, nullable=True),
            )

    inspector = sa.inspect(bind)
    indexes = {item['name'] for item in inspector.get_indexes('donations')}
    if 'ix_donations_gateway_order_id' not in indexes:
        op.create_index(
            'ix_donations_gateway_order_id',
            'donations',
            ['gateway_order_id'],
            unique=False,
        )
    if 'ix_donations_gateway_payment_id' not in indexes:
        op.create_index(
            'ix_donations_gateway_payment_id',
            'donations',
            ['gateway_payment_id'],
            unique=True,
            postgresql_where=sa.text('gateway_payment_id IS NOT NULL'),
            sqlite_where=sa.text('gateway_payment_id IS NOT NULL'),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {item['name'] for item in inspector.get_indexes('donations')}
    for name in ('ix_donations_gateway_payment_id', 'ix_donations_gateway_order_id'):
        if name in indexes:
            op.drop_index(name, table_name='donations')

    columns = {column['name'] for column in sa.inspect(bind).get_columns('donations')}
    for name in ('gateway_signature', 'gateway_payment_id', 'gateway_order_id'):
        if name in columns:
            op.drop_column(name, table_name='donations')
