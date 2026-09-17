from unittest.mock import Mock, patch

import pytest

from app.utils.storage_driver import StorageDriver


def _response(status_code, payload):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


def test_storage_error_code_supports_new_and_legacy_shapes():
    assert StorageDriver._storage_error_code(_response(409, {'code': 'ResourceAlreadyExists'})) == 'ResourceAlreadyExists'
    assert StorageDriver._storage_error_code(_response(409, {'error': 'Duplicate'})) == 'Duplicate'
    assert StorageDriver._storage_error_code(_response(400, {'error': {'code': 'InvalidMimeType'}})) == 'InvalidMimeType'
    assert StorageDriver._storage_error_code(_response(400, {'httpStatusCode': 400, 'message': 'private detail'})) is None


def test_storage_error_class_maps_supabase_codes():
    assert StorageDriver._storage_error_class('ResourceAlreadyExists', 409) == 'already_exists'
    assert StorageDriver._storage_error_class('Duplicate', 400) == 'already_exists'
    assert StorageDriver._storage_error_class('NoSuchBucket', 404) == 'bucket_unavailable'
    assert StorageDriver._storage_error_class('InvalidMimeType', 400) == 'invalid_mime_type'
    assert StorageDriver._storage_error_class('EntityTooLarge', 400) == 'too_large'
    assert StorageDriver._storage_error_class('MissingContentLength', 411) == 'missing_content_length'
    assert StorageDriver._storage_error_class('AccessDenied', 403) == 'access_denied'


@pytest.mark.parametrize(
    ('payload', 'status', 'message'),
    [
        ({'code': 'ResourceAlreadyExists', 'message': 'private'}, 409, 'Storage object already exists'),
        ({'error': 'Duplicate', 'message': 'private'}, 400, 'Storage object already exists'),
        ({'code': 'InvalidMimeType', 'message': 'private'}, 400, 'rejected this document MIME type'),
        ({'code': 'NoSuchBucket', 'message': 'private'}, 404, 'configured private storage bucket is unavailable'),
    ],
)
def test_upload_file_uses_structured_provider_code_without_leaking_message(app, payload, status, message):
    with app.app_context():
        app.config['SUPABASE_URL'] = 'https://example.supabase.co'
        app.config['SUPABASE_SERVICE_ROLE_KEY'] = 'test-service-role-key'
        app.config['SUPABASE_STORAGE_BUCKET'] = 'mandal-financial-documents'
        app.config['APP_ENV'] = 'production'

        response = _response(status, payload)
        with patch('app.utils.storage_driver.requests.post', return_value=response):
            with pytest.raises((ValueError, RuntimeError)) as exc_info:
                StorageDriver.upload_file(b'%PDF-test', 'documents/expense/ref/v1/file.pdf', 'application/pdf')

        assert message in str(exc_info.value)
        assert 'private' not in str(exc_info.value)
