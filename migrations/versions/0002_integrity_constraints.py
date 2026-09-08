"""Add database-level integrity constraints and indexes.

Revision ID: 0002_integrity_constraints
Revises: 0001_bootstrap

The bootstrap revision creates the current SQLAlchemy metadata, including
these named constraints. SQLite cannot add CHECK/UNIQUE constraints to an
existing table with a normal ALTER TABLE operation, so on a clean SQLite
bootstrap database the constraints are already present and this revision
only needs to add any missing indexes. PostgreSQL and other ALTER-capable
backends continue to receive the explicit constraint additions below.
"""

from alembic import op
from sqlalchemy import inspect


revision = "0002_integrity_constraints"
down_revision = "0001_bootstrap"
branch_labels = None
depends_on = None


def _constraint_exists(bind, table_name, constraint_name):
    inspector = inspect(bind)
    return any(
        constraint.get("name") == constraint_name
        for constraint in inspector.get_check_constraints(table_name)
    ) or any(
        constraint.get("name") == constraint_name
        for constraint in inspector.get_unique_constraints(table_name)
    )


def _index_exists(bind, table_name, index_name):
    inspector = inspect(bind)
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()

    # 0001_bootstrap creates the schema from the current SQLAlchemy metadata.
    # Those models already define every constraint below. SQLite cannot perform
    # these constraint ALTER operations in-place, and recreating these parent
    # tables would conflict with the foreign keys in the bootstrap schema.
    # Therefore a clean SQLite database already has the required constraints;
    # PostgreSQL and other ALTER-capable backends retain the explicit migration.
    if bind.dialect.name != "sqlite":
        checks = [
            ("ck_accounts_account_type", "accounts", "account_type IN ('cash', 'bank', 'upi')"),
            ("ck_accounts_opening_balance_nonnegative", "accounts", "opening_balance >= 0"),
            ("ck_transaction_categories_type", "transaction_categories", "category_type IN ('income', 'expense', 'transfer')"),
            ("ck_transactions_type", "transactions", "transaction_type IN ('INCOME', 'EXPENSE', 'TRANSFER', 'REVERSAL')"),
            ("ck_transactions_amount_positive", "transactions", "amount > 0"),
            ("ck_transactions_payment_mode", "transactions", "payment_mode IN ('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE', 'GATEWAY')"),
            ("ck_financial_year_dates", "financial_years", "start_date <= end_date"),
            ("ck_events_dates", "events", "start_date <= end_date"),
            ("ck_events_budget_target_nonnegative", "events", "budget_target >= 0"),
        ]

        for name, table, condition in checks:
            if not _constraint_exists(bind, table, name):
                op.create_check_constraint(name, table, condition)

        if not _constraint_exists(bind, "transaction_categories", "uq_transaction_categories_name_type"):
            op.create_unique_constraint(
                "uq_transaction_categories_name_type",
                "transaction_categories",
                ["name", "category_type"],
            )

    indexes = [
        ("ix_transactions_source", "transactions", ["source_module", "source_id"]),
        ("ix_transactions_account_date", "transactions", ["account_id", "transaction_date"]),
        ("ix_events_mandal_year", "events", ["mandal_id", "year"]),
    ]

    for name, table, columns in indexes:
        if not _index_exists(bind, table, name):
            op.create_index(name, table, columns)


def downgrade() -> None:
    bind = op.get_bind()

    for name, table in [
        ("ix_events_mandal_year", "events"),
        ("ix_transactions_account_date", "transactions"),
        ("ix_transactions_source", "transactions"),
    ]:
        if _index_exists(bind, table, name):
            op.drop_index(name, table_name=table)

    # SQLite cannot safely drop these constraints from the existing tables
    # without a batch table recreation. Keep downgrade non-destructive on the
    # development SQLite database; PostgreSQL retains the normal downgrade.
    if bind.dialect.name != "sqlite":
        for name, table, kind in [
            ("ck_events_budget_target_nonnegative", "events", "check"),
            ("ck_events_dates", "events", "check"),
            ("ck_financial_year_dates", "financial_years", "check"),
            ("ck_transactions_payment_mode", "transactions", "check"),
            ("ck_transactions_amount_positive", "transactions", "check"),
            ("ck_transactions_type", "transactions", "check"),
            ("ck_transaction_categories_type", "transaction_categories", "unique"),
            ("ck_accounts_opening_balance_nonnegative", "accounts", "check"),
            ("ck_accounts_account_type", "accounts", "check"),
        ]:
            if _constraint_exists(bind, table, name):
                op.drop_constraint(name, table, type_=kind)
