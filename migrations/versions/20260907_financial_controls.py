"""Financial controls: locks, corrections, contribution receipts, reconciliation and evidence rules.

Revision ID: 20260907_financial_controls
Revises: 9f2a7c1d4e6b
"""
from alembic import op
import sqlalchemy as sa

revision = '20260907_financial_controls'
down_revision = '9f2a7c1d4e6b'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('financial_years', sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('financial_years', sa.Column('locked_at', sa.DateTime(), nullable=True))
    op.add_column('financial_years', sa.Column('locked_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_financial_year_locked_by', 'financial_years', 'users', ['locked_by_id'], ['id'])

    op.add_column('events', sa.Column('status', sa.String(length=20), nullable=False, server_default='OPEN'))
    op.add_column('events', sa.Column('locked_at', sa.DateTime(), nullable=True))
    op.add_column('events', sa.Column('locked_by_id', sa.Integer(), nullable=True))
    op.add_column('events', sa.Column('closure_reason', sa.Text(), nullable=True))
    op.create_foreign_key('fk_events_locked_by', 'events', 'users', ['locked_by_id'], ['id'])
    op.create_check_constraint('ck_events_status', 'events', "status IN ('OPEN', 'CLOSED', 'LOCKED')")

    op.create_table(
        'contribution_receipts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('receipt_ref', sa.String(60), nullable=False, unique=True, index=True),
        sa.Column('source_type', sa.String(20), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False, index=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id'), nullable=False, index=True),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('accounts.id'), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('payment_mode', sa.String(30), nullable=False),
        sa.Column('external_ref', sa.String(100), nullable=True, index=True),
        sa.Column('transaction_id', sa.Integer(), sa.ForeignKey('transactions.id'), nullable=True, unique=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint("source_type IN ('SPONSORSHIP', 'MEMBER')", name='ck_contribution_receipts_source_type'),
        sa.CheckConstraint('amount > 0', name='ck_contribution_receipts_amount_positive'),
        sa.CheckConstraint("payment_mode IN ('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE', 'GATEWAY')", name='ck_contribution_receipts_payment_mode'),
    )
    op.create_table(
        'correction_requests',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('request_ref', sa.String(60), nullable=False, unique=True, index=True),
        sa.Column('entity_type', sa.String(40), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False, index=True),
        sa.Column('transaction_id', sa.Integer(), sa.ForeignKey('transactions.id'), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('requested_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reviewed_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('applied_reversal_id', sa.Integer(), sa.ForeignKey('transactions.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('PENDING', 'APPROVED', 'REJECTED', 'APPLIED')", name='ck_correction_status'),
    )
    op.create_table(
        'reconciliation_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('reconciliation_ref', sa.String(60), nullable=False, unique=True, index=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id'), nullable=True, index=True),
        sa.Column('account_id', sa.Integer(), sa.ForeignKey('accounts.id'), nullable=False, index=True),
        sa.Column('statement_date', sa.Date(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('book_balance', sa.Numeric(15, 2), nullable=False),
        sa.Column('statement_balance', sa.Numeric(15, 2), nullable=False),
        sa.Column('difference', sa.Numeric(15, 2), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='OPEN'),
        sa.Column('external_reference', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('resolved_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('OPEN', 'MATCHED', 'ADJUSTMENT_REQUIRED', 'RESOLVED')", name='ck_reconciliation_status'),
    )
    op.create_table(
        'evidence_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(150), nullable=False, unique=True),
        sa.Column('entity_type', sa.String(40), nullable=False),
        sa.Column('min_amount', sa.Numeric(15, 2), nullable=True),
        sa.Column('required_categories', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table('evidence_rules')
    op.drop_table('reconciliation_records')
    op.drop_table('correction_requests')
    op.drop_table('contribution_receipts')
    op.drop_constraint('ck_events_status', 'events', type_='check')
    op.drop_constraint('fk_events_locked_by', 'events', type_='foreignkey')
    for col in ('closure_reason', 'locked_by_id', 'locked_at', 'status'):
        op.drop_column('events', col)
    op.drop_constraint('fk_financial_year_locked_by', 'financial_years', type_='foreignkey')
    for col in ('locked_by_id', 'locked_at', 'is_locked'):
        op.drop_column('financial_years', col)
