"""Bootstrap the required mandal master record for operational event setup.

Revision ID: 20260911_mandal_bootstrap
Revises: 20260909_audit_immutability
"""

from alembic import op
import sqlalchemy as sa

revision = '20260911_mandal_bootstrap'
down_revision = '20260909_audit_immutability'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    mandals = sa.table(
        'mandals',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('location', sa.String),
        sa.column('registration_number', sa.String),
        sa.column('contact_phone', sa.String),
        sa.column('contact_email', sa.String),
        sa.column('description', sa.Text),
    )

    # The application cannot create an Event without a Mandal, while the
    # production database may legitimately be empty after schema-only deploys.
    # Seed only the master record required to make the operational event
    # workflow usable. Do not create a financial event automatically: event
    # activation must remain an explicit operational decision.
    exists = bind.execute(sa.select(mandals.c.id).limit(1)).first()
    if exists is None:
        bind.execute(
            mandals.insert().values(
                name='Shree Ashtavinayak Ganesh Utsav Mandal',
                location='Panchasheel Nagar, Gittikhadan, Nagpur, Maharashtra, India',
            )
        )


def downgrade():
    # Preserve an administrator-created mandal. This migration only bootstraps
    # the missing master record and must never delete production data on rollback.
    pass
