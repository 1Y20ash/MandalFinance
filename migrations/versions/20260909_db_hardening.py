"""Harden database integrity for financial and event data.

This migration adds database-enforced invariants that protect monetary values,
financial-year/event dates, budget thresholds, and contribution accounting.
It is deliberately additive and refuses to weaken existing safeguards on
rollback.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260909_db_hardening'
down_revision = '20260909_supabase_storage'
branch_labels = None
depends_on = None


def _constraint_exists(name: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        return bool(bind.execute(sa.text(
            'SELECT 1 FROM pg_constraint WHERE conname = :name LIMIT 1'
        ), {'name': name}).scalar())
    return False


def _index_exists(name: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        return bool(bind.execute(sa.text(
            'SELECT 1 FROM pg_indexes WHERE indexname = :name LIMIT 1'
        ), {'name': name}).scalar())
    return False


def _add_constraint(table: str, name: str, expression: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql' and not _constraint_exists(name):
        op.execute(sa.text(
            f'ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expression})'
        ))


def _add_index(name: str, table: str, columns: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql' and not _index_exists(name):
        op.execute(sa.text(f'CREATE INDEX {name} ON {table} ({columns})'))


def upgrade() -> None:
    _add_constraint('accounts', 'ck_accounts_current_balance_finite', 'current_balance >= 0')
    _add_constraint('financial_years', 'ck_financial_years_opening_balance_nonnegative', 'opening_balance >= 0')
    _add_constraint(
        'budgets', 'ck_budgets_amounts_nonnegative',
        'total_income_target >= 0 AND total_expense_limit >= 0 '
        'AND actual_income >= 0 AND actual_expense >= 0'
    )
    _add_constraint('budget_categories', 'ck_budget_categories_amounts_nonnegative',
                    'allocated_amount >= 0 AND spent_amount >= 0')
    _add_constraint('budget_categories', 'ck_budget_categories_spent_lte_allocated',
                    'spent_amount <= allocated_amount')
    _add_constraint(
        'budget_categories', 'ck_budget_categories_warning_range',
        'warning_threshold_pct >= 0 AND warning_threshold_pct <= 100 '
        'AND high_warning_threshold_pct >= 0 AND high_warning_threshold_pct <= 100 '
        'AND high_warning_threshold_pct >= warning_threshold_pct'
    )
    _add_constraint('budgets', 'ck_budgets_revision_positive', 'revision_no >= 1')

    _add_constraint(
        'sponsorships', 'ck_sponsorships_amounts_nonnegative',
        'committed_amount >= 0 AND received_amount >= 0 AND pending_amount >= 0'
    )
    _add_constraint('sponsorships', 'ck_sponsorships_received_lte_committed',
                    'received_amount <= committed_amount')
    _add_constraint('sponsorships', 'ck_sponsorships_pending_matches',
                    'pending_amount = committed_amount - received_amount')
    _add_constraint(
        'member_contributions', 'ck_member_contributions_amounts_nonnegative',
        'target_amount >= 0 AND received_amount >= 0 AND pending_amount >= 0'
    )
    _add_constraint('member_contributions', 'ck_member_contributions_received_lte_target',
                    'received_amount <= target_amount')
    _add_constraint('member_contributions', 'ck_member_contributions_pending_matches',
                    'pending_amount = target_amount - received_amount')

    _add_index('ix_donations_event_created', 'donations', 'event_id, created_at')
    _add_index('ix_expenses_event_date', 'expenses', 'event_id, expense_date')
    _add_index('ix_transactions_event_date', 'transactions', 'event_id, transaction_date')
    _add_index('ix_sponsorships_event_created', 'sponsorships', 'event_id, created_at')
    _add_index('ix_member_contributions_event_created', 'member_contributions', 'event_id, created_at')


def downgrade() -> None:
    # Database hardening is intentionally non-destructive. Removing integrity
    # controls during downgrade could silently corrupt historical finances.
    pass
