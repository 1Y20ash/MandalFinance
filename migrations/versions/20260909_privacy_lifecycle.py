"""Add consent records and Data Principal privacy request workflow."""
from alembic import op
import sqlalchemy as sa

revision = '20260909_privacy_lifecycle'
down_revision = ('9f2a7c1d4e6b', '20260908_contribution_payments')
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if 'consent_records' not in tables:
        op.create_table(
            'consent_records',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('purpose', sa.String(100), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='GRANTED'),
            sa.Column('notice_version', sa.String(40), nullable=False),
            sa.Column('source', sa.String(40), nullable=False, server_default='web'),
            sa.Column('granted_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('withdrawn_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint("status IN ('GRANTED', 'WITHDRAWN')", name='ck_consent_status'),
            sa.UniqueConstraint('user_id', 'purpose', 'notice_version', name='uq_consent_user_purpose_version'),
        )
        op.create_index('ix_consent_records_user_id', 'consent_records', ['user_id'])
        op.create_index('ix_consent_records_purpose', 'consent_records', ['purpose'])

    if 'privacy_requests' not in tables:
        op.create_table(
            'privacy_requests',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('request_type', sa.String(30), nullable=False),
            sa.Column('status', sa.String(30), nullable=False, server_default='REQUESTED'),
            sa.Column('details', sa.Text(), nullable=True),
            sa.Column('response_note', sa.Text(), nullable=True),
            sa.Column('requested_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('verified_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
            sa.Column('reviewed_by_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.CheckConstraint(
                "request_type IN ('ACCESS', 'CORRECTION', 'DELETION', 'WITHDRAW_CONSENT', 'GRIEVANCE')",
                name='ck_privacy_request_type',
            ),
            sa.CheckConstraint(
                "status IN ('REQUESTED', 'IDENTITY_VERIFIED', 'REVIEWED', 'PROCESSED', 'COMPLETED', 'REJECTED')",
                name='ck_privacy_request_status',
            ),
        )
        op.create_index('ix_privacy_requests_user_id', 'privacy_requests', ['user_id'])
        op.create_index('ix_privacy_requests_request_type', 'privacy_requests', ['request_type'])
        op.create_index('ix_privacy_requests_status', 'privacy_requests', ['status'])


def downgrade():
    # Privacy evidence and request history should not be destructively removed.
    pass
