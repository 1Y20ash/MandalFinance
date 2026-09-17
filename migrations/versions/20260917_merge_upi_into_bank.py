"""Merge the starter UPI receiving account into Main Bank.

Revision ID: 20260917_merge_upi_into_bank
Revises: 20260917_account_seeds

UPI is treated as a payment method rather than a separate ledger account.
Existing UPI transactions are reassigned to Main Bank and the UPI account's
opening/current balances are folded into Main Bank. The old UPI row is kept
but deactivated so historical foreign-key references remain valid while the
receiving-account dropdown exposes only Cash and Bank.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260917_merge_upi_into_bank'
down_revision = '20260917_account_seeds'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    accounts = sa.table(
        'accounts',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('account_type', sa.String),
        sa.column('opening_balance', sa.Numeric),
        sa.column('current_balance', sa.Numeric),
        sa.column('is_active', sa.Boolean),
    )
    transactions = sa.table(
        'transactions',
        sa.column('id', sa.Integer),
        sa.column('account_id', sa.Integer),
    )

    bank = bind.execute(
        sa.select(accounts).where(accounts.c.name == 'Main Bank')
    ).mappings().first()
    upi = bind.execute(
        sa.select(accounts).where(accounts.c.name == 'Main UPI')
    ).mappings().first()

    if bank is None:
        bind.execute(
            accounts.insert().values(
                name='Main Bank',
                account_type='bank',
                opening_balance=sa.literal(0).cast(sa.Numeric(15, 2)),
                current_balance=sa.literal(0).cast(sa.Numeric(15, 2)),
                is_active=True,
            )
        )
        bank = bind.execute(
            sa.select(accounts).where(accounts.c.name == 'Main Bank')
        ).mappings().first()

    if upi is None:
        return

    # Preserve the financial history while consolidating the account.
    bind.execute(
        transactions.update()
        .where(transactions.c.account_id == upi['id'])
        .values(account_id=bank['id'])
    )

    bind.execute(
        accounts.update()
        .where(accounts.c.id == bank['id'])
        .values(
            opening_balance=sa.func.coalesce(accounts.c.opening_balance, 0)
            + sa.literal(upi['opening_balance'] or 0),
            current_balance=sa.func.coalesce(accounts.c.current_balance, 0)
            + sa.literal(upi['current_balance'] or 0),
        )
    )

    # Keep the row for historical references, but hide it from active account
    # pickers. UPI remains a supported transaction payment mode.
    bind.execute(
        accounts.update()
        .where(accounts.c.id == upi['id'])
        .values(is_active=False)
    )


def downgrade():
    # Do not attempt to move transactions or balances back automatically.
    # The UPI account remains available as an inactive historical row.
    pass
