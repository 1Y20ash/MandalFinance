"""Enforce controlled private-storage metadata for financial evidence."""

from alembic import op

revision = '20260909_supabase_storage'
down_revision = '20260909_doc_security'
branch_labels = None
depends_on = None


def _pg_constraint_exists(name: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return False
    return bool(bind.exec_driver_sql(
        'SELECT 1 FROM pg_constraint WHERE conname = %s LIMIT 1', (name,)
    ).scalar())


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return

    constraints = (
        (
            'ck_documents_storage_provider',
            "ALTER TABLE documents ADD CONSTRAINT ck_documents_storage_provider "
            "CHECK (storage_provider IN ('LOCAL', 'SUPABASE'))",
        ),
        (
            'ck_documents_storage_path_nonempty',
            "ALTER TABLE documents ADD CONSTRAINT ck_documents_storage_path_nonempty "
            "CHECK (length(trim(storage_path)) > 0)",
        ),
        (
            'ck_document_versions_storage_provider',
            "ALTER TABLE document_versions ADD CONSTRAINT ck_document_versions_storage_provider "
            "CHECK (storage_provider IN ('LOCAL', 'SUPABASE'))",
        ),
        (
            'ck_document_versions_storage_path_nonempty',
            "ALTER TABLE document_versions ADD CONSTRAINT ck_document_versions_storage_path_nonempty "
            "CHECK (length(trim(storage_path)) > 0)",
        ),
    )
    for name, statement in constraints:
        if not _pg_constraint_exists(name):
            op.execute(statement)


def downgrade() -> None:
    # Storage-provider integrity is part of the production evidence-storage
    # contract. Do not silently weaken it on downgrade.
    pass
