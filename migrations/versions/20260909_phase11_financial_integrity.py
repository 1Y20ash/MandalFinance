"""Harden financial integrity invariants for Phase 11."""
from alembic import op
import sqlalchemy as sa

# Alembic's default version_num column is VARCHAR(32). Keep revision IDs within
# that limit so clean PostgreSQL migrations can advance the version table.
revision = '20260909_phase11_integrity'
down_revision = '20260908_contribution_payments'
branch_labels = None
depends_on = None

SOURCE_INDEX = 'uq_transactions_active_source'
EXTERNAL_INDEX = 'uq_transactions_external_ref'
PAYMENT_INDEX = 'uq_expenses_payment_ref'
RECON_INDEX = 'uq_reconciliation_account_statement_date'


def _index_exists(bind, table_name, index_name):
    return any(index.get('name') == index_name for index in sa.inspect(bind).get_indexes(table_name))


def _constraint_exists(bind, table_name, constraint_name):
    inspector = sa.inspect(bind)
    checks = inspector.get_check_constraints(table_name)
    uniques = inspector.get_unique_constraints(table_name)
    return any(x.get('name') == constraint_name for x in checks + uniques)


def upgrade():
    bind = op.get_bind()
    missing_checks = [
        ('ck_transactions_reversed_has_reversal', 'is_reversed = 0 OR reversed_by_txn_id IS NOT NULL' if bind.dialect.name == 'sqlite' else 'is_reversed = FALSE OR reversed_by_txn_id IS NOT NULL'),
        ('ck_transactions_reversal_reference', "transaction_type <> 'REVERSAL' OR external_ref LIKE 'REVERSAL-OF-%'"),
    ]

    if bind.dialect.name == 'sqlite':
        missing = [item for item in missing_checks if not _constraint_exists(bind, 'transactions', item[0])]
        if missing:
            with op.batch_alter_table('transactions', recreate='always') as batch:
                for name, condition in missing:
                    batch.create_check_constraint(name, condition)
    else:
        for name, condition in missing_checks:
            if not _constraint_exists(bind, 'transactions', name):
                op.create_check_constraint(name, 'transactions', condition)

    if not _index_exists(bind, 'transactions', SOURCE_INDEX):
        op.create_index(
            SOURCE_INDEX, 'transactions', ['source_module', 'source_id'], unique=True,
            postgresql_where=sa.text('source_id IS NOT NULL AND is_reversed = FALSE'),
            sqlite_where=sa.text('source_id IS NOT NULL AND is_reversed = 0'),
        )
    if not _index_exists(bind, 'transactions', EXTERNAL_INDEX):
        op.create_index(
            EXTERNAL_INDEX, 'transactions', ['external_ref'], unique=True,
            postgresql_where=sa.text('external_ref IS NOT NULL'),
            sqlite_where=sa.text('external_ref IS NOT NULL'),
        )
    if not _index_exists(bind, 'expenses', PAYMENT_INDEX):
        op.create_index(
            PAYMENT_INDEX, 'expenses', ['payment_ref'], unique=True,
            postgresql_where=sa.text('payment_ref IS NOT NULL'),
            sqlite_where=sa.text('payment_ref IS NOT NULL'),
        )

    if not _constraint_exists(bind, 'reconciliation_records', RECON_INDEX):
        if bind.dialect.name == 'sqlite':
            with op.batch_alter_table('reconciliation_records', recreate='always') as batch:
                batch.create_unique_constraint(RECON_INDEX, ['account_id', 'statement_date'])
        else:
            op.create_unique_constraint(RECON_INDEX, 'reconciliation_records', ['account_id', 'statement_date'])


def downgrade():
    bind = op.get_bind()
    for table, index_name in (
        ('expenses', PAYMENT_INDEX),
        ('transactions', EXTERNAL_INDEX),
        ('transactions', SOURCE_INDEX),
    ):
        if _index_exists(bind, table, index_name):
            op.drop_index(index_name, table_name=table)

    if _constraint_exists(bind, 'reconciliation_records', RECON_INDEX):
        if bind.dialect.name == 'sqlite':
            with op.batch_alter_table('reconciliation_records', recreate='always') as batch:
                batch.drop_constraint(RECON_INDEX, type_='unique')
        else:
            op.drop_constraint(RECON_INDEX, 'reconciliation_records', type_='unique')

    checks = ['ck_transactions_reversal_reference', 'ck_transactions_reversed_has_reversal']
    if bind.dialect.name == 'sqlite':
        existing = [name for name in checks if _constraint_exists(bind, 'transactions', name)]
        if existing:
            with op.batch_alter_table('transactions', recreate='always') as batch:
                for name in existing:
                    batch.drop_constraint(name, type_='check')
    else:
        for name in checks:
            if _constraint_exists(bind, 'transactions', name):
                op.drop_constraint(name, 'transactions', type_='check')
