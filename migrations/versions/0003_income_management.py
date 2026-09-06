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
    op.create_index('ix_income_entries_income_ref', 'income_entries', ['income_ref'], unique=False)
    op.create_index('ix_income_entries_event_id', 'income_entries', ['event_id'], unique=False)
    op.create_index('ix_income_entries_category_id', 'income_entries', ['category_id'], unique=False)
    op.create_index('ix_income_entries_account_id', 'income_entries', ['account_id'], unique=False)
    op.create_index('ix_income_entries_income_date', 'income_entries', ['income_date'], unique=False)
    op.create_index('ix_income_entries_transaction_ref', 'income_entries', ['transaction_ref'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_income_entries_transaction_ref', table_name='income_entries')
    op.drop_index('ix_income_entries_income_date', table_name='income_entries')
    op.drop_index('ix_income_entries_account_id', table_name='income_entries')
    op.drop_index('ix_income_entries_category_id', table_name='income_entries')
    op.drop_index('ix_income_entries_event_id', table_name='income_entries')
    op.drop_index('ix_income_entries_income_ref', table_name='income_entries')
    op.drop_table('income_entries')
