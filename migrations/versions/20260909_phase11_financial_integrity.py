"""Harden financial ledger invariants for Phase 11.

Revision ID: 20260909_phase11_financial_integrity
Revises: 20260908_contribution_payments
"""

from alembic import op
import sqlalchemy as sa


revision = '20260909_phase11_financial_integrity'
down_revision = '20260908_contribution_payments'
branch_labels = None
depends_on = None


SOURCE_INDEX = 'uq_transactions_active_source'
EXTERNAL_INDEX = 'uq_transactions_external_ref'


def _index_exists(bind, table_name, index_name):
    return any(index.get('name') == index_name for index in sa.inspect(bind).get_indexes(table_name))


def _check_exists(bind, table_name, constraint_name):
    return any(
        constraint.get('name') == constraint_name
        for constraint in sa.inspect(bind).get_check_constraints(table_name)
    )


def upgrade():
    bind = op.get_bind()

    if bind.dialect.name == 'sqlite':
        # The application metadata already contains these checks for clean
        # SQLite databases. Existing SQLite databases need batch recreation.
        with op.batch_alter_table('transactions', recreate='always') as batch:
            if not _check_exists(bind, 'transactions', 'ck_transactions_reversed_has_reversal'):
                batch.create_check_constraint(
                    'ck_transactions_reversed_has_reversal',
                    'is_reversed = 0 OR reversed_by_txn_id IS NOT NULL',
                )
            if not _check_exists(bind, 'transactions', 'ck_transactions_reversal_reference'):
                batch.create_check_constraint(
                    'ck_transactions_reversal_reference',
                    "transaction_type <> 'REVERSAL' OR external_ref LIKE 'REVERSAL-OF-%'",
                )

    elif not _check_exists(bind, 'transactions', 'ck_transactions_reversed_has_reversal'):
        op.create_check_constraint(
            'ck_transactions_reversed_has_reversal',
            'transactions',
            'is_reversed = FALSE OR reversed_by_txn_id IS NOT NULL',
        )

    if bind.dialect.name != 'sqlite' and not _check_exists(bind, 'transactions', 'ck_transactions_reversal_reference'):
        op.create_check_constraint(
            'ck_transactions_reversal_reference',
            'transactions',
            "transaction_type <> 'REVERSAL' OR external_ref LIKE 'REVERSAL-OF-%'",
        )

    if not _index_exists(bind, 'transactions', SOURCE_INDEX):
        op.create_index(
            SOURCE_INDEX,
            'transactions',
            ['source_module', 'source_id'],
            unique=True,
            postgresql_where=sa.text('source_id IS NOT NULL AND is_reversed = FALSE'),
            sqlite_where=sa.text('source_id IS NOT NULL AND is_reversed = 0'),
        )

    if not _index_exists(bind, 'transactions', EXTERNAL_INDEX):
        op.create_index(
            EXTERNAL_INDEX,
            'transactions',
            ['external_ref'],
            unique=True,
            postgresql_where=sa.text('external_ref IS NOT NULL'),
            sqlite_where=sa.text('external_ref IS NOT NULL'),
        )


def downgrade():
    bind = op.get_bind()
    if _index_exists(bind, 'transactions', EXTERNAL_INDEX):
        op.drop_index(EXTERNAL_INDEX, table_name='transactions')
    if _index_exists(bind, 'transactions', SOURCE_INDEX):
        op.drop_index(SOURCE_INDEX, table_name='transactions')

    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('transactions', recreate='always') as batch:
            if _check_exists(bind, 'transactions', 'ck_transactions_reversal_reference'):
                batch.drop_constraint('ck_transactions_reversal_reference', type_='check')
            if _check_exists(bind, 'transactions', 'ck_transactions_reversed_has_reversal'):
                batch.drop_constraint('ck_transactions_reversed_has_reversal', type_='check')
    else:
        if _check_exists(bind, 'transactions', 'ck_transactions_reversal_reference'):
            op.drop_constraint('ck_transactions_reversal_reference', 'transactions', type_='check')
        if _check_exists(bind, 'transactions', 'ck_transactions_reversed_has_reversal'):
            op.drop_constraint('ck_transactions_reversed_has_reversal', 'transactions', type_='check')
