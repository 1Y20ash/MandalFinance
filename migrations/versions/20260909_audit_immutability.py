"""Harden audit history with immutable, tamper-evident event metadata.

Revision ID: 20260909_audit_immutability
Revises: 20260909_merge_doc_income
"""

import hashlib
import json
import uuid

import sqlalchemy as sa
from alembic import op

revision = '20260909_audit_immutability'
down_revision = '20260909_merge_doc_income'
branch_labels = None
depends_on = None


def _canonical(row):
    return json.dumps({
        'event_id': row.event_id,
        'user_id': row.user_id,
        'user_email': row.user_email,
        'action': row.action,
        'entity_type': row.entity_type,
        'entity_id': row.entity_id,
        'description': row.description,
        'details': row.details,
        'outcome': row.outcome,
        'request_id': row.request_id,
        'ip_address': row.ip_address,
        'user_agent': row.user_agent,
        'created_at': row.created_at.isoformat() if row.created_at else None,
    }, sort_keys=True, separators=(',', ':'))


def _backfill(bind):
    table = sa.table(
        'audit_logs',
        sa.column('id', sa.Integer()),
        sa.column('event_id', sa.String()),
        sa.column('user_id', sa.Integer()),
        sa.column('user_email', sa.String()),
        sa.column('action', sa.String()),
        sa.column('entity_type', sa.String()),
        sa.column('entity_id', sa.String()),
        sa.column('description', sa.Text()),
        sa.column('details', sa.Text()),
        sa.column('outcome', sa.String()),
        sa.column('request_id', sa.String()),
        sa.column('ip_address', sa.String()),
        sa.column('user_agent', sa.String()),
        sa.column('created_at', sa.DateTime()),
        sa.column('integrity_hash', sa.String()),
    )
    rows = bind.execute(sa.select(table).order_by(table.c.id.asc())).mappings().all()
    for row in rows:
        event_id = row['event_id'] or str(uuid.uuid4())
        outcome = row['outcome'] or 'success'
        payload = {
            'event_id': event_id,
            'user_id': row['user_id'],
            'user_email': row['user_email'],
            'action': row['action'],
            'entity_type': row['entity_type'],
            'entity_id': row['entity_id'],
            'description': row['description'],
            'details': row['details'],
            'outcome': outcome,
            'request_id': row['request_id'],
            'ip_address': row['ip_address'],
            'user_agent': row['user_agent'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
        }
        integrity_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
        ).hexdigest()
        bind.execute(
            table.update().where(table.c.id == row['id']).values(
                event_id=event_id,
                outcome=outcome,
                integrity_hash=integrity_hash,
            )
        )


def upgrade():
    bind = op.get_bind()
    op.add_column('audit_logs', sa.Column('event_id', sa.String(length=36), nullable=True))
    op.add_column('audit_logs', sa.Column('outcome', sa.String(length=20), nullable=True))
    op.add_column('audit_logs', sa.Column('request_id', sa.String(length=128), nullable=True))
    op.add_column('audit_logs', sa.Column('integrity_hash', sa.String(length=64), nullable=True))

    _backfill(bind)

    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('audit_logs', recreate='always') as batch:
            batch.alter_column('event_id', existing_type=sa.String(length=36), nullable=False)
            batch.alter_column('outcome', existing_type=sa.String(length=20), nullable=False)
            batch.alter_column('integrity_hash', existing_type=sa.String(length=64), nullable=False)
    else:
        op.alter_column('audit_logs', 'event_id', existing_type=sa.String(length=36), nullable=False)
        op.alter_column('audit_logs', 'outcome', existing_type=sa.String(length=20), nullable=False)
        op.alter_column('audit_logs', 'integrity_hash', existing_type=sa.String(length=64), nullable=False)

    op.create_index('ix_audit_logs_event_id', 'audit_logs', ['event_id'], unique=True)
    op.create_index('ix_audit_logs_integrity_hash', 'audit_logs', ['integrity_hash'], unique=True)
    op.create_index('ix_audit_logs_request_id', 'audit_logs', ['request_id'], unique=False)
    op.create_index('ix_audit_logs_outcome', 'audit_logs', ['outcome'], unique=False)

    if bind.dialect.name == 'postgresql':
        op.execute(sa.text("""
            CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                RAISE EXCEPTION 'audit_logs are append-only and cannot be updated or deleted';
            END;
            $$;
        """))
        op.execute(sa.text("""
            CREATE TRIGGER audit_logs_immutable
            BEFORE UPDATE OR DELETE ON audit_logs
            FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation();
        """))


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute(sa.text('DROP TRIGGER IF EXISTS audit_logs_immutable ON audit_logs'))
        op.execute(sa.text('DROP FUNCTION IF EXISTS prevent_audit_log_mutation()'))

    op.drop_index('ix_audit_logs_outcome', table_name='audit_logs')
    op.drop_index('ix_audit_logs_request_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_integrity_hash', table_name='audit_logs')
    op.drop_index('ix_audit_logs_event_id', table_name='audit_logs')
    op.drop_column('audit_logs', 'integrity_hash')
    op.drop_column('audit_logs', 'request_id')
    op.drop_column('audit_logs', 'outcome')
    op.drop_column('audit_logs', 'event_id')
