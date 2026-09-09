"""Store structured data submitted for correction requests."""
from alembic import op
import sqlalchemy as sa

revision = '20260909_privacy_request_data'
down_revision = '20260909_privacy_lifecycle'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column['name'] for column in inspector.get_columns('privacy_requests')}

    # Keep the migration safe for databases where the model/schema already
    # contains the column (for example, a prior development migration).
    if 'requested_data' not in columns:
        op.add_column('privacy_requests', sa.Column('requested_data', sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column['name'] for column in inspector.get_columns('privacy_requests')}

    if 'requested_data' in columns:
        op.drop_column('privacy_requests', 'requested_data')
