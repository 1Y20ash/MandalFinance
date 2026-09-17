"""Seed the standard income transaction categories.

Revision ID: 20260917_income_categories
Revises: 20260911_online_gateway

The Record Income form reads income categories from transaction_categories.
The schema migrations previously created the table but did not provide any
production seed rows, leaving the category dropdown empty on a schema-only
installation. This migration inserts the standard categories idempotently.
"""

from alembic import op
import sqlalchemy as sa

revision = '20260917_income_categories'
down_revision = '20260911_online_gateway'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    categories = sa.table(
        'transaction_categories',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('category_type', sa.String),
        sa.column('description', sa.String),
        sa.column('is_system', sa.Boolean),
    )

    standard_categories = [
        ('Donations', 'Donations received from contributors and supporters.'),
        ('Sponsorship', 'Sponsorship income received for the festival.'),
        ('Stall Rental', 'Income received from festival stall rentals.'),
        ('Bank Interest', 'Interest credited by banks or financial accounts.'),
        ('Other Income', 'Other legitimate income not covered by a specific category.'),
    ]

    for name, description in standard_categories:
        exists = bind.execute(
            sa.select(sa.literal(1)).select_from(categories).where(
                sa.and_(
                    categories.c.name == name,
                    categories.c.category_type == 'income',
                )
            )
        ).first()
        if exists is None:
            bind.execute(
                categories.insert().values(
                    name=name,
                    category_type='income',
                    description=description,
                    is_system=True,
                )
            )


def downgrade():
    # Seeded categories may already be referenced by financial transactions.
    # Never delete financial master data during a migration rollback.
    pass
