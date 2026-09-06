"""Add database-level integrity constraints and indexes.

Revision ID: 0002_integrity_constraints
Revises: 0001_bootstrap
"""

from alembic import op


revision = "0002_integrity_constraints"
down_revision = "0001_bootstrap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The application models are the canonical definition of these checks.
    # PostgreSQL receives the constraints explicitly here so existing
    # databases can be hardened through a normal Alembic migration.
    op.create_check_constraint(
        "ck_accounts_account_type",
        "accounts",
        "account_type IN ('cash', 'bank', 'upi')",
    )
    op.create_check_constraint(
        "ck_accounts_opening_balance_nonnegative",
        "accounts",
        "opening_balance >= 0",
    )
    op.create_unique_constraint(
        "uq_transaction_categories_name_type",
        "transaction_categories",
        ["name", "category_type"],
    )
    op.create_check_constraint(
        "ck_transaction_categories_type",
        "transaction_categories",
        "category_type IN ('income', 'expense', 'transfer')",
    )
    op.create_check_constraint(
        "ck_transactions_type",
        "transactions",
        "transaction_type IN ('INCOME', 'EXPENSE', 'TRANSFER', 'REVERSAL')",
    )
    op.create_check_constraint(
        "ck_transactions_amount_positive",
        "transactions",
        "amount > 0",
    )
    op.create_check_constraint(
        "ck_transactions_payment_mode",
        "transactions",
        "payment_mode IN ('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE', 'GATEWAY')",
    )
    op.create_check_constraint(
        "ck_financial_year_dates",
        "financial_years",
        "start_date <= end_date",
    )
    op.create_check_constraint(
        "ck_events_dates",
        "events",
        "start_date <= end_date",
    )
    op.create_check_constraint(
        "ck_events_budget_target_nonnegative",
        "events",
        "budget_target >= 0",
    )

    op.create_index("ix_transactions_source", "transactions", ["source_module", "source_id"])
    op.create_index("ix_transactions_account_date", "transactions", ["account_id", "transaction_date"])
    op.create_index("ix_events_mandal_year", "events", ["mandal_id", "year"])


def downgrade() -> None:
    op.drop_index("ix_events_mandal_year", table_name="events")
    op.drop_index("ix_transactions_account_date", table_name="transactions")
    op.drop_index("ix_transactions_source", table_name="transactions")

    op.drop_constraint("ck_events_budget_target_nonnegative", "events", type_="check")
    op.drop_constraint("ck_events_dates", "events", type_="check")
    op.drop_constraint("ck_financial_year_dates", "financial_years", type_="check")
    op.drop_constraint("ck_transactions_payment_mode", "transactions", type_="check")
    op.drop_constraint("ck_transactions_amount_positive", "transactions", type_="check")
    op.drop_constraint("ck_transactions_type", "transactions", type_="check")
    op.drop_constraint("ck_transaction_categories_type", "transaction_categories", type_="check")
    op.drop_constraint("uq_transaction_categories_name_type", "transaction_categories", type_="unique")
    op.drop_constraint("ck_accounts_opening_balance_nonnegative", "accounts", type_="check")
    op.drop_constraint("ck_accounts_account_type", "accounts", type_="check")
