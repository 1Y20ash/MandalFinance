from app.models.auth import User
from app.services.document_service import DocumentService
from app.utils.hash_utils import compute_sha256

def test_document_hash_versioning_and_integrity_check(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        content_v1 = b"Invoice Content v1 - Ashtavinayak Mandal"
        hash_v1 = compute_sha256(content_v1)

        # Upload Version 1
        doc = DocumentService.upload_document(
            file_bytes=content_v1,
            filename="bill.pdf",
            file_type="application/pdf",
            category="BILL",
            title="Stage Bill",
            entity_type="EXPENSE",
            uploader_user=user,
            entity_id=1
        )

        assert doc.current_version_number == 1
        assert doc.current_sha256_hash == hash_v1

        # Verify Integrity
        is_match, rec_hash, comp_hash = DocumentService.verify_document_integrity(doc.id)
        assert is_match is True
        assert rec_hash == comp_hash == hash_v1

        # Replace with Version 2
        content_v2 = b"Invoice Content v2 Updated - Ashtavinayak Mandal"
        hash_v2 = compute_sha256(content_v2)

        doc = DocumentService.replace_document(
            document_id=doc.id,
            new_file_bytes=content_v2,
            new_filename="bill_updated.pdf",
            new_file_type="application/pdf",
            uploader_user=user,
            replacement_reason="Updated bill amount"
        )

        assert doc.current_version_number == 2
        assert doc.current_sha256_hash == hash_v2
        assert len(doc.versions) == 2
