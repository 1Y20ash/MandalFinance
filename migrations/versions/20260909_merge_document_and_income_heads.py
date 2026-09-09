"""Merge the document-security and income-ledger migration heads.

Revision ID: 20260909_merge_doc_income
Revises: 20260909_doc_security, 20260909_income_link
"""

revision = '20260909_merge_doc_income'
down_revision = ('20260909_doc_security', '20260909_income_link')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
