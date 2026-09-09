"""Store structured data submitted for correction requests."""
from alembic import op
import sqlalchemy as sa

revision = '20260909_privacy_request_data'
down_revision = '20260909_privacy_lifecycle'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('privacy_requests', sa.Column('requested_data', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('privacy_requests', 'requested_data')
