"""Verify production PostgreSQL integrity controls after migrations.

This is intentionally separate from the SQLite regression fixture. The CI
pipeline uses it immediately after a clean PostgreSQL migration so database
constraints and indexes are tested against the same engine used in production.
"""

from pathlib import Path
import sys

# When this file is executed directly (``python scripts/...``), Python puts
# ``scripts/`` on sys.path rather than the repository root. Add the root so
# the application package can be imported reliably in CI and locally.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import text

from app import create_app
from app.extensions import db


REQUIRED_CONSTRAINTS = {
    'accounts': {'ck_accounts_current_balance_finite'},
    'financial_years': {'ck_financial_years_opening_balance_nonnegative'},
    'budgets': {'ck_budgets_amounts_nonnegative', 'ck_budgets_revision_positive'},
    'budget_categories': {
        'ck_budget_categories_amounts_nonnegative',
        'ck_budget_categories_spent_lte_allocated',
        'ck_budget_categories_warning_range',
    },
    'sponsorships': {
        'ck_sponsorships_amounts_nonnegative',
        'ck_sponsorships_received_lte_committed',
        'ck_sponsorships_pending_matches',
    },
    'member_contributions': {
        'ck_member_contributions_amounts_nonnegative',
        'ck_member_contributions_received_lte_target',
        'ck_member_contributions_pending_matches',
    },
}

REQUIRED_INDEXES = {
    'ix_donations_event_created',
    'ix_expenses_event_date',
    'ix_transactions_event_date',
    'ix_sponsorships_event_created',
    'ix_member_contributions_event_created',
}


def main() -> None:
    app = create_app('development')
    with app.app_context():
        bind = db.session.get_bind()
        if bind.dialect.name != 'postgresql':
            raise SystemExit('PostgreSQL schema verification requires PostgreSQL')

        # Read the catalog once and compare sets in Python. This avoids driver-
        # specific array binding behaviour for PostgreSQL's ``ANY(:names)``
        # expression and makes the verifier deterministic across environments.
        constraint_rows = db.session.execute(text(
            "SELECT conname FROM pg_constraint "
            "WHERE connamespace = current_schema()::regnamespace"
        )).scalars()
        found_constraints = set(constraint_rows)
        expected_constraints = {name for names in REQUIRED_CONSTRAINTS.values() for name in names}
        missing_constraints = expected_constraints - found_constraints
        if missing_constraints:
            raise SystemExit(f'Missing PostgreSQL constraints: {sorted(missing_constraints)}')

        index_rows = db.session.execute(text(
            "SELECT indexname FROM pg_indexes WHERE schemaname = current_schema()"
        )).scalars()
        found_indexes = set(index_rows)
        missing_indexes = REQUIRED_INDEXES - found_indexes
        if missing_indexes:
            raise SystemExit(f'Missing PostgreSQL indexes: {sorted(missing_indexes)}')

        print('PostgreSQL schema contract verified')


if __name__ == '__main__':
    main()
