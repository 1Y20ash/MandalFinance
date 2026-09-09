from pathlib import Path

import pytest

from app.utils.storage_driver import StorageDriver


def test_storage_paths_reject_traversal(app):
    with app.app_context():
        for value in ('../secret.pdf', 'documents/../secret.pdf', r'documents\\..\\secret.pdf', '/absolute/path.pdf'):
            with pytest.raises(ValueError):
                StorageDriver.safe_relative_path(value)


def test_storage_object_names_are_unpredictable(app):
    with app.app_context():
        first = StorageDriver.object_name('documents/general/DOC-2026-ABCD/v1', 'pdf')
        second = StorageDriver.object_name('documents/general/DOC-2026-ABCD/v1', 'pdf')
        assert first != second
        assert first.startswith('documents/general/DOC-2026-ABCD/v1/')
        assert first.endswith('.pdf')
        assert len(first.rsplit('/', 1)[1].split('.')[0]) == 48


def test_local_storage_never_escapes_upload_root(app, tmp_path):
    with app.app_context():
        outside = tmp_path / 'outside.txt'
        outside.write_bytes(b'secret')
        with pytest.raises(ValueError):
            StorageDriver.get_file('LOCAL', '../outside.txt')
        with pytest.raises(ValueError):
            StorageDriver.delete_file('LOCAL', '../outside.txt')


def test_local_storage_upload_is_no_overwrite(app):
    with app.app_context():
        provider, path = StorageDriver.upload_file(b'hello', 'documents/test/unique.txt', 'text/plain')
        assert provider == 'LOCAL'
        assert StorageDriver.object_exists(provider, path) is True
        with pytest.raises(ValueError, match='already exists'):
            StorageDriver.upload_file(b'changed', path, 'text/plain')
        assert StorageDriver.get_file(provider, path) == b'hello'
        assert StorageDriver.delete_file(provider, path) is True
        assert StorageDriver.object_exists(provider, path) is False


def test_signed_url_requires_supabase_and_bounded_expiry(app):
    with app.app_context():
        with pytest.raises(ValueError, match='only supported'):
            StorageDriver.create_signed_url('LOCAL', 'documents/test/file.pdf')
        with pytest.raises(ValueError, match='between 60 and 900'):
            StorageDriver.create_signed_url('SUPABASE', 'documents/test/file.pdf', 30)
        with pytest.raises(ValueError, match='between 60 and 900'):
            StorageDriver.create_signed_url('SUPABASE', 'documents/test/file.pdf', 901)


def test_signed_url_never_uses_client_supplied_storage_key(app, monkeypatch):
    with app.app_context():
        app.config.update(
            SUPABASE_URL='https://example.supabase.co',
            SUPABASE_SERVICE_ROLE_KEY='server-only-secret',
            SUPABASE_STORAGE_BUCKET='private-documents',
            SUPABASE_STORAGE_PRIVATE=True,
        )
        captured = {}

        class FakeResponse:
            status_code = 200

            def json(self):
                return {'signedURL': '/storage/v1/object/sign/private-documents/documents/test.pdf?token=short'}

        def fake_post(endpoint, **kwargs):
            captured['endpoint'] = endpoint
            captured['headers'] = kwargs['headers']
            captured['json'] = kwargs['json']
            return FakeResponse()

        monkeypatch.setattr('app.utils.storage_driver.requests.post', fake_post)
        signed = StorageDriver.create_signed_url('SUPABASE', 'documents/test.pdf', 300)
        assert signed.startswith('https://example.supabase.co/storage/v1/object/sign/')
        assert captured['json'] == {'expiresIn': 300}
        assert captured['headers']['Authorization'] == 'Bearer server-only-secret'
        assert captured['headers']['apikey'] == 'server-only-secret'
        assert 'server-only-secret' not in signed
