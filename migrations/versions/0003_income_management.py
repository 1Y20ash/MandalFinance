"""Create non-donation income management table.

Revision ID: 0003_income_management
Revises: 0002_integrity_constraints
"""

from alembic import op
import sqlalchemy as sa

revision = '0003_income_management'
down_revision = '0002_integrity_constraints'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'income_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('income_ref', sa.String(length=50), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('income_date', sa.Date(), nullable=False),
        sa.Column('payment_mode', sa.String(length=30), nullable=False),
        sa.Column('transaction_ref', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('transaction_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('amount > 0', name='ck_income_entries_amount_positive'),
        sa.CheckConstraint("payment_mode IN ('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE')", name='ck_income_entries_payment_mode'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id']),
        sa.ForeignKeyConstraint(['category_id'], ['transaction_categories.id']),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id']),
        sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('income_ref', name='uq_income_entries_income_ref'),
        sa.UniqueConstraint('transaction_id', name='uq_income_entries_transaction_id'),
    )
    for name, columns in [
        ('ix_income_entries_income_ref', ['income_ref']),
        ('ix_income_entries_event_id', ['event_id']),
        ('ix_income_entries_category_id', ['category_id']),
        ('ix_income_entries_account_id', ['account_id']),
        ('ix_income_entries_income_date', ['income_date']),
        ('ix_income_entries_transaction_ref', ['transaction_ref']),
    ]:
        op.create_index(name, 'income_entries', columns, unique=False)

    permissions = sa.table(
        'permissions',
        sa.column('name', sa.String), sa.column('description', sa.String), sa.column('module', sa.String),
    )
    bind = op.get_bind()
    for name, description in [
        ('income.view', 'View income records'),
        ('income.create', 'Create income records'),
    ]:
        exists = bind.execute(sa.select(sa.literal(1)).select_from(permissions).where(permissions.c.name == name)).first()
        if not exists:
            op.bulk_insert(permissions, [{'name': name, 'description': description, 'module': 'income'}])


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table('permissions', sa.column('name', sa.String))
    bind.execute(permissions.delete().where(permissions.c.name.in_(['income.view', 'income.create'])))
    for name in ['ix_income_entries_transaction_ref', 'ix_income_entries_income_date', 'ix_income_entries_account_id', 'ix_income_entries_category_id', 'ix_income_entries_event_id', 'ix_income_entries_income_ref']:
        op.drop_index(name, table_name='income_entries')
    op.drop_table('income_entries')
