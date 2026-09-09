"""Harden document/version integrity constraints for private evidence storage."""

from alembic import op
import sqlalchemy as sa

revision = '20260909_doc_security'
down_revision = '20260909_payment_event'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # The bootstrap migration builds from SQLAlchemy metadata. On a fresh
    # database these constraints may therefore already exist. Existing/stamped
    # databases from the older model still need them added here.
    version_constraints = {
        item.get('name') for item in inspector.get_unique_constraints('document_versions')
    }
    version_indexes = {
        item.get('name') for item in inspector.get_indexes('document_versions')
    }
    if 'uq_document_version_number' not in version_constraints and 'uq_document_version_number' not in version_indexes:
        if bind.dialect.name != 'sqlite':
            op.create_unique_constraint(
                'uq_document_version_number', 'document_versions', ['document_id', 'version_number']
            )

    if bind.dialect.name == 'sqlite':
        # SQLite cannot safely add table constraints with ALTER TABLE. The
        # SQLAlchemy model enforces these validation boundaries for test/local
        # databases, while PostgreSQL receives database-level constraints.
        return

    existing_checks = {
        item.get('name') for item in inspector.get_check_constraints('documents')
    }
    if 'ck_documents_file_size_nonnegative' not in existing_checks:
        op.create_check_constraint(
            'ck_documents_file_size_nonnegative', 'documents', 'file_size >= 0'
        )
    if 'ck_documents_version_positive' not in existing_checks:
        op.create_check_constraint(
            'ck_documents_version_positive', 'documents', 'current_version_number >= 1'
        )

    version_checks = {
        item.get('name') for item in inspector.get_check_constraints('document_versions')
    }
    if 'ck_document_versions_file_size_nonnegative' not in version_checks:
        op.create_check_constraint(
            'ck_document_versions_file_size_nonnegative', 'document_versions', 'file_size >= 0'
        )
    if 'ck_document_versions_version_positive' not in version_checks:
        op.create_check_constraint(
            'ck_document_versions_version_positive', 'document_versions', 'version_number >= 1'
        )


def downgrade() -> None:
    # These safeguards are part of the current model baseline. Do not remove
    # them on downgrade because doing so could silently weaken an existing DB.
    pass
