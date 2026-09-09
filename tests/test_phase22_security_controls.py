import pytest

from app.utils.security import is_safe_local_redirect
from app.utils.storage_driver import StorageDriver


def test_open_redirect_validation_accepts_only_local_paths():
    assert is_safe_local_redirect('/dashboard') is True
    assert is_safe_local_redirect('/auth/profile?tab=security') is True
    assert is_safe_local_redirect('https://attacker.example/') is False
    assert is_safe_local_redirect('//attacker.example/') is False
    assert is_safe_local_redirect('javascript:alert(1)') is False
    assert is_safe_local_redirect('dashboard') is False


def test_storage_rejects_path_traversal():
    for path in ('../secret.txt', '/etc/passwd', 'C:/secret.txt', 'documents/../secret.txt'):
        with pytest.raises(ValueError, match='Unsafe storage path'):
            StorageDriver.safe_relative_path(path)


def test_storage_sanitizes_untrusted_filenames():
    assert StorageDriver.sanitize_filename('../../statement.pdf') == 'statement.pdf'
    assert StorageDriver.sanitize_filename(r'..\\..\\statement.pdf') == 'statement.pdf'
    assert '<script>' not in StorageDriver.sanitize_filename('<script>alert(1)</script>.pdf')


def test_storage_rejects_mismatched_document_type():
    with pytest.raises(ValueError, match='MIME type'):
        StorageDriver.validate_document(b'%PDF-1.7', 'evidence.pdf', 'image/png')


def test_storage_rejects_invalid_pdf_signature():
    with pytest.raises(ValueError, match='content does not match'):
        StorageDriver.validate_document(b'not a pdf', 'evidence.pdf', 'application/pdf')
