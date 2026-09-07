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


def _inspector(bind):
    return sa.inspect(bind)


def _constraint_exists(bind, table_name, constraint_name):
    inspector = _inspector(bind)
    checks = inspector.get_check_constraints(table_name)
    uniques = inspector.get_unique_constraints(table_name)
    foreign_keys = inspector.get_foreign_keys(table_name)
    return any(c.get('name') == constraint_name for c in checks + uniques + foreign_keys)


def _index_exists(bind, table_name, index_name):
    return any(i.get('name') == index_name for i in _inspector(bind).get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = _inspector(bind)
    dialect = bind.dialect.name
    columns = {column['name'] for column in inspector.get_columns('users')}

    # PostgreSQL supports direct ALTER TABLE operations and has many foreign
    # keys referencing users.id. Avoid Alembic's recreate='always' batch mode,
    # which attempts to drop users_pkey and therefore conflicts with those FKs.
    if dialect != 'sqlite':
        if 'approval_status' not in columns:
            op.add_column('users', sa.Column('approval_status', sa.String(length=20), nullable=True))
        if 'requested_at' not in columns:
            op.add_column('users', sa.Column('requested_at', sa.DateTime(), nullable=True))
        if 'reviewed_at' not in columns:
            op.add_column('users', sa.Column('reviewed_at', sa.DateTime(), nullable=True))
        if 'approved_by_id' not in columns:
            op.add_column('users', sa.Column('approved_by_id', sa.Integer(), nullable=True))
        if 'rejection_reason' not in columns:
            op.add_column('users', sa.Column('rejection_reason', sa.String(length=500), nullable=True))
    else:
        # SQLite needs batch mode for ALTER TABLE operations. Only use it when
        # a real schema change is necessary; never force a table recreation on
        # a metadata-created baseline that already contains these columns.
        missing = {'approval_status', 'requested_at', 'reviewed_at', 'approved_by_id', 'rejection_reason'} - columns
        if missing:
            with op.batch_alter_table('users', schema=None, recreate='always') as batch_op:
                if 'approval_status' in missing:
                    batch_op.add_column(sa.Column('approval_status', sa.String(length=20), nullable=True))
                if 'requested_at' in missing:
                    batch_op.add_column(sa.Column('requested_at', sa.DateTime(), nullable=True))
                if 'reviewed_at' in missing:
                    batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(), nullable=True))
                if 'approved_by_id' in missing:
                    batch_op.add_column(sa.Column('approved_by_id', sa.Integer(), nullable=True))
                if 'rejection_reason' in missing:
                    batch_op.add_column(sa.Column('rejection_reason', sa.String(length=500), nullable=True))

    # Existing accounts predate the approval workflow and must remain usable.
    op.execute("UPDATE users SET approval_status = 'APPROVED' WHERE approval_status IS NULL")

    inspector = _inspector(bind)
    indexes = {index['name'] for index in inspector.get_indexes('users')}
    if 'ix_users_approval_status' not in indexes:
        op.create_index('ix_users_approval_status', 'users', ['approval_status'], unique=False)

    inspector = _inspector(bind)
    foreign_keys = inspector.get_foreign_keys('users')
    has_reviewer_fk = any(
        fk.get('referred_table') == 'users'
        and fk.get('constrained_columns') == ['approved_by_id']
        for fk in foreign_keys
    )
    if not has_reviewer_fk:
        if dialect != 'sqlite':
            op.create_foreign_key(
                'fk_users_approved_by_id_users',
                'users',
                ['approved_by_id'],
                ['id'],
            )
        else:
            with op.batch_alter_table('users', schema=None, recreate='always') as batch_op:
                batch_op.create_foreign_key(
                    'fk_users_approved_by_id_users',
                    'users',
                    ['approved_by_id'],
                    ['id'],
                )

    inspector = _inspector(bind)
    constraints = {constraint.get('name') for constraint in inspector.get_check_constraints('users')}
    if 'ck_users_approval_status' not in constraints:
        if dialect != 'sqlite':
            op.create_check_constraint(
                'ck_users_approval_status',
                'users',
                "approval_status IN ('PENDING', 'APPROVED', 'REJECTED')",
            )
        else:
            with op.batch_alter_table('users', schema=None, recreate='always') as batch_op:
                batch_op.create_check_constraint(
                    'ck_users_approval_status',
                    "approval_status IN ('PENDING', 'APPROVED', 'REJECTED')",
                )

    inspector = _inspector(bind)
    nullable = next(
        column['nullable'] for column in inspector.get_columns('users')
        if column['name'] == 'approval_status'
    )
    if nullable:
        if dialect != 'sqlite':
            op.alter_column(
                'users',
                'approval_status',
                existing_type=sa.String(length=20),
                nullable=False,
            )
        else:
            with op.batch_alter_table('users', schema=None, recreate='always') as batch_op:
                batch_op.alter_column(
                    'approval_status',
                    existing_type=sa.String(length=20),
                    nullable=False,
                )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect != 'sqlite':
        inspector = _inspector(bind)
        if any(i.get('name') == 'ix_users_approval_status' for i in inspector.get_indexes('users')):
            op.drop_index('ix_users_approval_status', table_name='users')
        if _constraint_exists(bind, 'users', 'ck_users_approval_status'):
            op.drop_constraint('ck_users_approval_status', 'users', type_='check')
        inspector = _inspector(bind)
        if any(
            fk.get('name') == 'fk_users_approved_by_id_users'
            for fk in inspector.get_foreign_keys('users')
        ):
            op.drop_constraint('fk_users_approved_by_id_users', 'users', type_='foreignkey')
        for column in ('rejection_reason', 'approved_by_id', 'reviewed_at', 'requested_at', 'approval_status'):
            if any(c['name'] == column for c in _inspector(bind).get_columns('users')):
                op.drop_column('users', column)
    else:
        with op.batch_alter_table('users', schema=None, recreate='always') as batch_op:
            batch_op.drop_constraint('ck_users_approval_status', type_='check')
            batch_op.drop_constraint('fk_users_approved_by_id_users', type_='foreignkey')
            batch_op.drop_column('rejection_reason')
            batch_op.drop_column('approved_by_id')
            batch_op.drop_column('reviewed_at')
            batch_op.drop_column('requested_at')
            batch_op.drop_column('approval_status')
        if _index_exists(bind, 'users', 'ix_users_approval_status'):
            op.drop_index('ix_users_approval_status', table_name='users')
