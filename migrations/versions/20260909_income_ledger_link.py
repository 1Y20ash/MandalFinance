"""Allow atomic income-to-ledger linking during Phase 11 writes."""
from alembic import op
import sqlalchemy as sa

revision = '20260909_income_link'
down_revision = '20260909_phase11_integrity'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('income_entries', recreate='always') as batch:
            batch.alter_column('transaction_id', existing_type=sa.Integer(), existing_nullable=False, nullable=True)
    else:
        op.alter_column('income_entries', 'transaction_id', existing_type=sa.Integer(), existing_nullable=False, nullable=True)


def downgrade():
    bind = op.get_bind()
    null_count = bind.execute(sa.text('SELECT COUNT(*) FROM income_entries WHERE transaction_id IS NULL')).scalar_one()
    if null_count:
        raise RuntimeError(
            'Cannot restore income_entries.transaction_id NOT NULL while '
            f'{null_count} income row(s) have no ledger transaction.'
        )
    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('income_entries', recreate='always') as batch:
            batch.alter_column('transaction_id', existing_type=sa.Integer(), existing_nullable=True, nullable=False)
    else:
        op.alter_column('income_entries', 'transaction_id', existing_type=sa.Integer(), existing_nullable=True, nullable=False)
