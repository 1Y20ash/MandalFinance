"""Harden document/version integrity constraints for private evidence storage."""

from alembic import op

revision = '20260909_doc_security'
down_revision = '20260909_payment_event'
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
        # SQLite's CREATE TABLE path already receives the model constraints.
        # Avoid ALTER TABLE constraint operations that SQLite does not support.
        return

    constraints = (
        ('uq_document_version_number',
         'ALTER TABLE document_versions ADD CONSTRAINT uq_document_version_number UNIQUE (document_id, version_number)'),
        ('ck_documents_file_size_nonnegative',
         'ALTER TABLE documents ADD CONSTRAINT ck_documents_file_size_nonnegative CHECK (file_size >= 0)'),
        ('ck_documents_version_positive',
         'ALTER TABLE documents ADD CONSTRAINT ck_documents_version_positive CHECK (current_version_number >= 1)'),
        ('ck_document_versions_file_size_nonnegative',
         'ALTER TABLE document_versions ADD CONSTRAINT ck_document_versions_file_size_nonnegative CHECK (file_size >= 0)'),
        ('ck_document_versions_version_positive',
         'ALTER TABLE document_versions ADD CONSTRAINT ck_document_versions_version_positive CHECK (version_number >= 1)'),
    )
    for name, statement in constraints:
        if not _pg_constraint_exists(name):
            op.execute(statement)


def downgrade() -> None:
    # These safeguards are part of the current model baseline. Do not remove
    # them on downgrade because doing so could silently weaken an existing DB.
    pass
