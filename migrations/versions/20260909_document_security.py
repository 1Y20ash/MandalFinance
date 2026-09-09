"""Harden document/version integrity constraints for private evidence storage."""

from alembic import op
import sqlalchemy as sa

revision = '20260909_doc_security'
# Merge the financial-integrity and income-ledger-link branches before applying
# document hardening. Both parent revisions are part of the same clean upgrade.
down_revision = ('20260909_fin_integrity', '20260909_income_link')
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {item['name'] for item in inspector.get_indexes('document_versions')}
    constraints = {item['name'] for item in inspector.get_unique_constraints('document_versions')}

    if 'uq_document_version_number' not in constraints and 'uq_document_version_number' not in indexes:
        if bind.dialect.name == 'sqlite':
            # SQLite cannot ALTER a table to add a UNIQUE constraint. Alembic's
            # batch mode recreates the table while preserving existing columns,
            # foreign keys, indexes, and constraints.
            with op.batch_alter_table('document_versions', recreate='always') as batch:
                batch.create_unique_constraint(
                    'uq_document_version_number', ['document_id', 'version_number']
                )
        else:
            op.create_unique_constraint(
                'uq_document_version_number', 'document_versions', ['document_id', 'version_number']
            )

    # SQLite cannot add CHECK constraints through ALTER TABLE in the same way as
    # PostgreSQL. The application model enforces these at validation time there;
    # PostgreSQL receives the database-level checks through the normal migration.
    dialect = bind.dialect.name
    if dialect != 'sqlite':
        for name, table, condition in (
            ('ck_documents_file_size_nonnegative', 'documents', 'file_size >= 0'),
            ('ck_documents_version_positive', 'documents', 'current_version_number >= 1'),
            ('ck_document_versions_file_size_nonnegative', 'document_versions', 'file_size >= 0'),
            ('ck_document_versions_version_positive', 'document_versions', 'version_number >= 1'),
        ):
            existing_checks = {item['name'] for item in sa.inspect(bind).get_check_constraints(table)}
            if name not in existing_checks:
                op.create_check_constraint(name, table, condition)


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
