"""Seed the standard receiving accounts used by financial entry forms.

Revision ID: 20260917_account_seeds
Revises: 20260917_income_categories

The Record Income form loads receiving accounts from the accounts table. The
schema baseline creates that table but does not create operational account
rows, so a clean/schema-only production database can render an empty account
dropdown. This migration adds zero-balance starter accounts idempotently.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260917_account_seeds'
down_revision = '20260917_income_categories'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    accounts = sa.table(
        'accounts',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('account_type', sa.String),
        sa.column('account_number', sa.String),
        sa.column('bank_name', sa.String),
        sa.column('ifsc_code', sa.String),
        sa.column('upi_id', sa.String),
        sa.column('opening_balance', sa.Numeric),
        sa.column('current_balance', sa.Numeric),
        sa.column('is_active', sa.Boolean),
    )

    standard_accounts = [
        ('Main Cash', 'cash'),
        ('Main Bank', 'bank'),
        ('Main UPI', 'upi'),
    ]

    for name, account_type in standard_accounts:
        exists = bind.execute(
            sa.select(sa.literal(1)).select_from(accounts).where(
                accounts.c.name == name
            )
        ).first()
        if exists is None:
            bind.execute(
                accounts.insert().values(
                    name=name,
                    account_type=account_type,
                    opening_balance=sa.literal(0).cast(sa.Numeric(15, 2)),
                    current_balance=sa.literal(0).cast(sa.Numeric(15, 2)),
                    is_active=True,
                )
            )


def downgrade():
    # These accounts are financial master data and may already be referenced
    # by transactions. Never delete them during migration rollback.
    pass
