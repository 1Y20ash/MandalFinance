"""Add user registration approval workflow.

Revision ID: 0004_user_registration_approval
Revises: 0003_donation_integrity, 0003_income_management
"""

from alembic import op
import sqlalchemy as sa

revision = '0004_user_registration_approval'
down_revision = ('0003_donation_integrity', '0003_income_management')
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column['name'] for column in inspector.get_columns('users')}

    with op.batch_alter_table('users', schema=None, recreate='always') as batch_op:
        if 'approval_status' not in columns:
            batch_op.add_column(sa.Column('approval_status', sa.String(length=20), nullable=True))
        if 'requested_at' not in columns:
            batch_op.add_column(sa.Column('requested_at', sa.DateTime(), nullable=True))
        if 'reviewed_at' not in columns:
            batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(), nullable=True))
        if 'approved_by_id' not in columns:
            batch_op.add_column(sa.Column('approved_by_id', sa.Integer(), nullable=True))
        if 'rejection_reason' not in columns:
            batch_op.add_column(sa.Column('rejection_reason', sa.String(length=500), nullable=True))

    # Existing accounts predate the approval workflow and must remain usable.
    op.execute("UPDATE users SET approval_status = 'APPROVED' WHERE approval_status IS NULL")

    inspector = sa.inspect(bind)
    indexes = {index['name'] for index in inspector.get_indexes('users')}
    if 'ix_users_approval_status' not in indexes:
        op.create_index('ix_users_approval_status', 'users', ['approval_status'], unique=False)

    # Add the self-referencing reviewer FK only when it does not already exist.
    foreign_keys = inspector.get_foreign_keys('users')
    has_reviewer_fk = any(
        fk.get('referred_table') == 'users' and fk.get('constrained_columns') == ['approved_by_id']
        for fk in foreign_keys
    )
    if not has_reviewer_fk:
        with op.batch_alter_table('users', schema=None, recreate='always') as batch_op:
            batch_op.create_foreign_key(
                'fk_users_approved_by_id_users',
                'users',
                ['approved_by_id'],
                ['id'],
            )

    # Constrain status values after existing rows have been backfilled.
    inspector = sa.inspect(bind)
    constraints = {constraint.get('name') for constraint in inspector.get_check_constraints('users')}
    if 'ck_users_approval_status' not in constraints:
        with op.batch_alter_table('users', schema=None, recreate='always') as batch_op:
            batch_op.create_check_constraint(
                'ck_users_approval_status',
                "approval_status IN ('PENDING', 'APPROVED', 'REJECTED')",
            )

    # Make the new state mandatory after backfilling legacy accounts.
    with op.batch_alter_table('users', schema=None, recreate='always') as batch_op:
        batch_op.alter_column('approval_status', existing_type=sa.String(length=20), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None, recreate='always') as batch_op:
        batch_op.drop_constraint('ck_users_approval_status', type_='check')
        batch_op.drop_constraint('fk_users_approved_by_id_users', type_='foreignkey')
        batch_op.drop_column('rejection_reason')
        batch_op.drop_column('approved_by_id')
        batch_op.drop_column('reviewed_at')
        batch_op.drop_column('requested_at')
        batch_op.drop_column('approval_status')

    op.drop_index('ix_users_approval_status', table_name='users')
