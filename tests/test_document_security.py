import io

import pytest

from app.extensions import db
from app.models.auth import User
from app.services.document_service import DocumentService
from app.utils.storage_driver import StorageDriver
from app.routes.documents import _validated_upload


def test_storage_path_is_unpredictable_and_never_contains_original_filename(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        doc = DocumentService.upload_document(
            b'%PDF-1.7\nsecure evidence', 'invoice final.pdf', 'application/pdf',
            'BILL', 'Secure invoice', 'EXPENSE', user, entity_id=1
        )
        assert doc.storage_path.startswith('documents/expense/')
        assert 'invoice' not in doc.storage_path.lower()
        assert doc.original_filename == 'invoice final.pdf'
        assert len(doc.storage_path.rsplit('/', 1)[-1].split('.', 1)[0]) >= 40


def test_upload_rejects_path_traversal_filename(app):
    with app.app_context():
        class Upload:
            filename = '../../secret.pdf'
            mimetype = 'application/pdf'

            @staticmethod
            def read(_size=-1):
                return b'%PDF-1.7\ncontent'

        content, filename, mime = _validated_upload(Upload())
        assert filename == 'secret.pdf'
        assert mime == 'application/pdf'
        assert content.startswith(b'%PDF-')
        assert '..' not in filename


def test_upload_rejects_mismatched_extension_and_mime(app):
    with app.app_context():
        class Upload:
            filename = 'invoice.exe'
            mimetype = 'application/pdf'

            @staticmethod
            def read(_size=-1):
                return b'%PDF-1.7\ncontent'

        with pytest.raises(ValueError, match='extension'):
            _validated_upload(Upload())


def test_upload_rejects_fake_pdf_signature(app):
    with app.app_context():
        class Upload:
            filename = 'invoice.pdf'
            mimetype = 'application/pdf'

            @staticmethod
            def read(_size=-1):
                return b'not really a pdf'

        with pytest.raises(ValueError, match='content'):
            _validated_upload(Upload())


def test_document_upload_is_atomic_with_version_creation(app):
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        doc = DocumentService.upload_document(
            b'%PDF-1.7\natomic', 'proof.pdf', 'application/pdf',
            'BILL', 'Atomic proof', 'EXPENSE', user, entity_id=1
        )
        db.session.expire_all()
        assert len(DocumentService._object_path('EXPENSE', doc.doc_ref, 1, 'proof.pdf').split('/')) == 5
        assert doc.versions[0].version_number == 1
        assert doc.versions[0].storage_path == doc.storage_path


def test_storage_path_rejects_traversal(app):
    with app.app_context():
        with pytest.raises(ValueError):
            StorageDriver.safe_relative_path('documents/../../outside')
        with pytest.raises(ValueError):
            StorageDriver.safe_relative_path('/absolute/path')
