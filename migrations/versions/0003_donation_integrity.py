"""Add integrity constraints for donations.

Revision ID: 0003_donation_integrity
Revises: 0002_integrity_constraints
"""

from alembic import op

revision = '0003_donation_integrity'
down_revision = '0002_integrity_constraints'
branch_labels = None
depends_on = None


def _constraint_exists(bind, table_name, constraint_name):
    from sqlalchemy import inspect
    inspector = inspect(bind)
    checks = inspector.get_check_constraints(table_name)
    uniques = inspector.get_unique_constraints(table_name)
    return any(c.get('name') == constraint_name for c in checks + uniques)


def _index_exists(bind, table_name, index_name):
    from sqlalchemy import inspect
    inspector = inspect(bind)
    return any(i.get('name') == index_name for i in inspector.get_indexes(table_name))


def upgrade():
    bind = op.get_bind()
    constraints = [
        ('ck_donations_amount_positive', 'amount > 0'),
        ('ck_donations_type', "donation_type IN ('ONLINE', 'OFFLINE')"),
        ('ck_donations_payment_mode', "payment_mode IN ('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE', 'ONLINE_GATEWAY')"),
        ('ck_donations_status', "status IN ('PENDING', 'SUCCESS', 'FAILED', 'CANCELLED')"),
    ]
    for name, condition in constraints:
        if not _constraint_exists(bind, 'donations', name):
            op.create_check_constraint(name, 'donations', condition)

    if not _constraint_exists(bind, 'donations', 'uq_donations_gateway_payment_id'):
        op.create_unique_constraint('uq_donations_gateway_payment_id', 'donations', ['gateway_payment_id'])


def downgrade():
    bind = op.get_bind()
    if _constraint_exists(bind, 'donations', 'uq_donations_gateway_payment_id'):
        op.drop_constraint('uq_donations_gateway_payment_id', 'donations', type_='unique')
    for name in (
        'ck_donations_status', 'ck_donations_payment_mode',
        'ck_donations_type', 'ck_donations_amount_positive',
    ):
        if _constraint_exists(bind, 'donations', name):
            op.drop_constraint(name, 'donations', type_='check')
