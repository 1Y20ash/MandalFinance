"""Harden document/version integrity constraints for private evidence storage."""

from alembic import op
import sqlalchemy as sa

revision = '20260909_doc_security'
down_revision = '20260909_phase11_financial_integrity'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {item['name'] for item in inspector.get_indexes('document_versions')}
    constraints = {item['name'] for item in inspector.get_unique_constraints('document_versions')}

    if 'uq_document_version_number' not in constraints and 'uq_document_version_number' not in indexes:
        op.create_unique_constraint(
            'uq_document_version_number', 'document_versions', ['document_id', 'version_number']
        )

    # SQLite cannot add CHECK constraints through ALTER TABLE in the same way as
    # PostgreSQL. The application model enforces these at validation time there;
    # PostgreSQL receives the database-level checks through the normal migration.
    dialect = bind.dialect.name
    if dialect != 'sqlite':
        op.create_check_constraint(
            'ck_documents_file_size_nonnegative', 'documents', 'file_size >= 0'
        )
        op.create_check_constraint(
            'ck_documents_version_positive', 'documents', 'current_version_number >= 1'
        )
        op.create_check_constraint(
            'ck_document_versions_file_size_nonnegative', 'document_versions', 'file_size >= 0'
        )
        op.create_check_constraint(
            'ck_document_versions_version_positive', 'document_versions', 'version_number >= 1'
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'sqlite':
        for name, table in (
            ('ck_document_versions_version_positive', 'document_versions'),
            ('ck_document_versions_file_size_nonnegative', 'document_versions'),
            ('ck_documents_version_positive', 'documents'),
            ('ck_documents_file_size_nonnegative', 'documents'),
        ):
            try:
                op.drop_constraint(name, table_name=table, type_='check')
            except Exception:
                pass
    try:
        op.drop_constraint('uq_document_version_number', 'document_versions', type_='unique')
    except Exception:
        pass
