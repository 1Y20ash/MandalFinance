"""Add reconciliation lines and PDP governance fields.

Revision ID: 20260907_pdp_hardening
Revises: 20260907_financial_controls
"""
from alembic import op
import sqlalchemy as sa

revision = '20260907_pdp_hardening'
down_revision = '20260907_financial_controls'
branch_labels = None
depends_on = None


def _inspector(bind):
    return sa.inspect(bind)


def _columns(bind, table):
    return {c['name'] for c in _inspector(bind).get_columns(table)}


def _tables(bind):
    return set(_inspector(bind).get_table_names())


def upgrade():
    bind = op.get_bind()
    tables = _tables(bind)
    if 'reconciliation_lines' not in tables:
        op.create_table(
            'reconciliation_lines',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('reconciliation_id', sa.Integer(), sa.ForeignKey('reconciliation_records.id', ondelete='CASCADE'), nullable=False),
            sa.Column('line_ref', sa.String(80), nullable=False),
            sa.Column('transaction_date', sa.Date(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('external_ref', sa.String(100), nullable=True),
            sa.Column('amount', sa.Numeric(15, 2), nullable=False),
            sa.Column('matched_transaction_id', sa.Integer(), sa.ForeignKey('transactions.id'), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='UNMATCHED'),
            sa.Column('match_note', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint('reconciliation_id', 'line_ref', name='uq_reconciliation_line_ref'),
            sa.CheckConstraint('amount > 0', name='ck_reconciliation_line_amount_positive'),
            sa.CheckConstraint("status IN ('UNMATCHED', 'MATCHED', 'IGNORED')", name='ck_reconciliation_line_status'),
        )
        op.create_index('ix_reconciliation_lines_reconciliation_id', 'reconciliation_lines', ['reconciliation_id'])
        op.create_index('ix_reconciliation_lines_external_ref', 'reconciliation_lines', ['external_ref'])
        op.create_index('ix_reconciliation_lines_matched_transaction_id', 'reconciliation_lines', ['matched_transaction_id'])

    if 'budgets' in tables:
        cols = _columns(bind, 'budgets')
        if 'status' not in cols:
            op.add_column('budgets', sa.Column('status', sa.String(20), nullable=False, server_default='DRAFT'))
        if 'approved_by_id' not in cols:
            op.add_column('budgets', sa.Column('approved_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))
        if 'approved_at' not in cols:
            op.add_column('budgets', sa.Column('approved_at', sa.DateTime(), nullable=True))
        if 'revision_no' not in cols:
            op.add_column('budgets', sa.Column('revision_no', sa.Integer(), nullable=False, server_default='1'))
        if 'revision_reason' not in cols:
            op.add_column('budgets', sa.Column('revision_reason', sa.Text(), nullable=True))
        op.create_check_constraint('ck_budget_status', 'budgets', "status IN ('DRAFT', 'APPROVED', 'REVISED', 'CLOSED')")


def downgrade():
    pass
