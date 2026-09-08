"""Add auditable payment ledgers for sponsorships and member contributions."""
from alembic import op
import sqlalchemy as sa

revision = '20260908_contribution_payments'
down_revision = '20260907_pdp_hardening'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'sponsorship_payments' not in tables:
        op.create_table(
            'sponsorship_payments',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('sponsorship_id', sa.Integer(), sa.ForeignKey('sponsorships.id'), nullable=False),
            sa.Column('amount', sa.Numeric(15, 2), nullable=False),
            sa.Column('payment_date', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('payment_mode', sa.String(30), nullable=False),
            sa.Column('transaction_ref', sa.String(100), nullable=True),
            sa.Column('account_id', sa.Integer(), sa.ForeignKey('accounts.id'), nullable=False),
            sa.Column('ledger_transaction_id', sa.Integer(), sa.ForeignKey('transactions.id'), nullable=True, unique=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint('amount > 0', name='ck_sponsorship_payment_amount_positive'),
            sa.CheckConstraint("payment_mode IN ('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE', 'GATEWAY')", name='ck_sponsorship_payment_mode'),
            sa.UniqueConstraint('sponsorship_id', 'transaction_ref', name='uq_sponsorship_payment_ref'),
        )
        op.create_index('ix_sponsorship_payments_sponsorship_id', 'sponsorship_payments', ['sponsorship_id'])
        op.create_index('ix_sponsorship_payments_transaction_ref', 'sponsorship_payments', ['transaction_ref'])

    if 'member_contribution_payments' not in tables:
        op.create_table(
            'member_contribution_payments',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('contribution_id', sa.Integer(), sa.ForeignKey('member_contributions.id'), nullable=False),
            sa.Column('amount', sa.Numeric(15, 2), nullable=False),
            sa.Column('payment_date', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('payment_mode', sa.String(30), nullable=False),
            sa.Column('transaction_ref', sa.String(100), nullable=True),
            sa.Column('account_id', sa.Integer(), sa.ForeignKey('accounts.id'), nullable=False),
            sa.Column('ledger_transaction_id', sa.Integer(), sa.ForeignKey('transactions.id'), nullable=True, unique=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint('amount > 0', name='ck_member_payment_amount_positive'),
            sa.CheckConstraint("payment_mode IN ('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE', 'GATEWAY')", name='ck_member_payment_mode'),
            sa.UniqueConstraint('contribution_id', 'transaction_ref', name='uq_member_payment_ref'),
        )
        op.create_index('ix_member_contribution_payments_contribution_id', 'member_contribution_payments', ['contribution_id'])
        op.create_index('ix_member_contribution_payments_transaction_ref', 'member_contribution_payments', ['transaction_ref'])


def downgrade():
    # Financial payment history is intentionally not destructively downgraded.
    pass
