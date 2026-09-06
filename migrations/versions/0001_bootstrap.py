"""Bootstrap the current MandalFinance SQLAlchemy schema.

Revision ID: 0001_bootstrap
Revises:
Create Date: 2026-09-06

This revision establishes a migration baseline for databases whose schema is
managed by the current SQLAlchemy models. It intentionally creates tables
from SQLAlchemy metadata rather than embedding a hand-written schema snapshot,
so the baseline remains aligned with the application models.

Existing databases that already contain the current schema should be stamped
at this revision instead of running the upgrade against populated tables.
All future schema changes must be separate Alembic revisions.
"""

from alembic import op

from app import db
import app.models  # noqa: F401

# revision identifiers, used by Alembic.
revision = "0001_bootstrap"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    db.metadata.create_all(bind=bind)


def downgrade() -> None:
    # The bootstrap revision is a baseline, not a destructive reset. A full
    # schema downgrade would risk deleting financial records.
    pass
