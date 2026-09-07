"""Add financial controls schema safely across existing and clean databases.

The 0001 bootstrap revision builds the current SQLAlchemy metadata, so a clean
migration database may already contain every column/table introduced here.
This revision therefore performs additive, schema-aware changes only.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260907_financial_controls'
down_revision = '9f2a7c1d4e6b'
branch_labels = None
depends_on = None


def _inspector(bind):
    return sa.inspect(bind)


def _table_exists(bind, table_name):
    return _inspector(bind).has_table(table_name)


def _columns(bind, table_name):
    return {c['name'] for c in _inspector(bind).get_columns(table_name)}


def _index_exists(bind, table_name, index_name):
    return any(i.get('name') == index_name for i in _inspector(bind).get_indexes(table_name))


def _constraint_exists(bind, table_name, constraint_name):
    inspector = _inspector(bind)
    constraints = []
    constraints.extend(inspector.get_check_constraints(table_name))
    constraints.extend(inspector.get_unique_constraints(table_name))
    constraints.extend(inspector.get_foreign_keys(table_name))
    return any(c.get('name') == constraint_name for c in constraints)


def _add_column_if_missing(bind, table_name, column):
    if column.name not in _columns(bind, table_name):
        op.add_column(table_name, column)


def _create_fk_if_missing(bind, table_name, name, columns, referred_table, referred_columns):
    if not _constraint_exists(bind, table_name, name):
        inspector = _inspector(bind)
        existing = inspector.get_foreign_keys(table_name)
        same_fk = any(
            fk.get('referred_table') == referred_table
            and fk.get('constrained_columns') == list(columns)
            and fk.get('referred_columns') == list(referred_columns)
            for fk in existing
        )
        if not same_fk:
            op.create_foreign_key(name, table_name, referred_table, list(columns), list(referred_columns))


def _create_check_if_missing(bind, table_name, name, condition):
    if not _constraint_exists(bind, table_name, name):
        op.create_check_constraint(name, table_name, condition)


def _create_control_tables(bind):
    if not _table_exists(bind, 'contribution_receipts'):
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

    if not _table_exists(bind, 'correction_requests'):
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
            sa.Column('review_note', sa.Text()),
            sa.Column('applied_reversal_id', sa.Integer(), sa.ForeignKey('transactions.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('reviewed_at', sa.DateTime()),
            sa.CheckConstraint("status IN ('PENDING','APPROVED','REJECTED','APPLIED')", name='ck_correction_status'),
        )

    if not _table_exists(bind, 'reconciliation_records'):
        op.create_table(
            'reconciliation_records',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('reconciliation_ref', sa.String(60), nullable=False, unique=True, index=True),
            sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id'), nullable=True, index=True),
            sa.Column('account_id', sa.Integer(), sa.ForeignKey('accounts.id'), nullable=False, index=True),
            sa.Column('statement_date', sa.Date(), nullable=False),
            sa.Column('period_start', sa.Date()),
            sa.Column('period_end', sa.Date()),
            sa.Column('book_balance', sa.Numeric(15, 2), nullable=False),
            sa.Column('statement_balance', sa.Numeric(15, 2), nullable=False),
            sa.Column('difference', sa.Numeric(15, 2), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='OPEN'),
            sa.Column('external_reference', sa.String(100)),
            sa.Column('notes', sa.Text()),
            sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('resolved_by_id', sa.Integer(), sa.ForeignKey('users.id')),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('resolved_at', sa.DateTime()),
            sa.CheckConstraint("status IN ('OPEN','MATCHED','ADJUSTMENT_REQUIRED','RESOLVED')", name='ck_reconciliation_status'),
        )

    if not _table_exists(bind, 'evidence_rules'):
        op.create_table(
            'evidence_rules',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(150), nullable=False, unique=True),
            sa.Column('entity_type', sa.String(40), nullable=False),
            sa.Column('min_amount', sa.Numeric(15, 2)),
            sa.Column('required_categories', sa.Text(), nullable=False),
            sa.Column('description', sa.Text()),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )


def upgrade():
    bind = op.get_bind()

    # 0001_bootstrap already contains these fields when the current models are
    # used as the baseline. Add them only for older schemas that lack them.
    _add_column_if_missing(bind, 'financial_years', sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column_if_missing(bind, 'financial_years', sa.Column('locked_at', sa.DateTime(), nullable=True))
    _add_column_if_missing(bind, 'financial_years', sa.Column('locked_by_id', sa.Integer(), nullable=True))
    _create_fk_if_missing(bind, 'financial_years', 'fk_financial_year_locked_by', ['locked_by_id'], 'users', ['id'])

    _add_column_if_missing(bind, 'events', sa.Column('status', sa.String(20), nullable=False, server_default='OPEN'))
    _add_column_if_missing(bind, 'events', sa.Column('locked_at', sa.DateTime(), nullable=True))
    _add_column_if_missing(bind, 'events', sa.Column('locked_by_id', sa.Integer(), nullable=True))
    _add_column_if_missing(bind, 'events', sa.Column('closure_reason', sa.Text(), nullable=True))
    _create_fk_if_missing(bind, 'events', 'fk_events_locked_by', ['locked_by_id'], 'users', ['id'])
    _create_check_if_missing(bind, 'events', 'ck_events_status', "status IN ('OPEN','CLOSED','LOCKED')")

    _create_control_tables(bind)


def downgrade():
    bind = op.get_bind()
    for table in ('evidence_rules', 'reconciliation_records', 'correction_requests', 'contribution_receipts'):
        if _table_exists(bind, table):
            op.drop_table(table)

    dialect = bind.dialect.name
    if dialect == 'sqlite':
        # SQLite requires batch recreation for column removal. This path is
        # primarily for local development; PostgreSQL uses direct ALTER TABLE.
        with op.batch_alter_table('events') as batch:
            if _constraint_exists(bind, 'events', 'ck_events_status'):
                batch.drop_constraint('ck_events_status', type_='check')
            if _constraint_exists(bind, 'events', 'fk_events_locked_by'):
                batch.drop_constraint('fk_events_locked_by', type_='foreignkey')
            for column in ('closure_reason', 'locked_by_id', 'locked_at', 'status'):
                if column in _columns(bind, 'events'):
                    batch.drop_column(column)
        with op.batch_alter_table('financial_years') as batch:
            if _constraint_exists(bind, 'financial_years', 'fk_financial_year_locked_by'):
                batch.drop_constraint('fk_financial_year_locked_by', type_='foreignkey')
            for column in ('locked_by_id', 'locked_at', 'is_locked'):
                if column in _columns(bind, 'financial_years'):
                    batch.drop_column(column)
    else:
        if _constraint_exists(bind, 'events', 'ck_events_status'):
            op.drop_constraint('ck_events_status', 'events', type_='check')
        if _constraint_exists(bind, 'events', 'fk_events_locked_by'):
            op.drop_constraint('fk_events_locked_by', 'events', type_='foreignkey')
        for column in ('closure_reason', 'locked_by_id', 'locked_at', 'status'):
            if column in _columns(bind, 'events'):
                op.drop_column('events', column)
        if _constraint_exists(bind, 'financial_years', 'fk_financial_year_locked_by'):
            op.drop_constraint('fk_financial_year_locked_by', 'financial_years', type_='foreignkey')
        for column in ('locked_by_id', 'locked_at', 'is_locked'):
            if column in _columns(bind, 'financial_years'):
                op.drop_column('financial_years', column)
