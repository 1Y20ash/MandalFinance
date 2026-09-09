import os
import re
import secrets
from pathlib import Path, PurePosixPath
from flask import current_app
import requests


class StorageDriver:
    """Controlled private-object storage adapter for financial evidence."""

    @staticmethod
    def sanitize_filename(filename):
        filename = os.path.basename(str(filename or '').replace('\\', '/')).strip()
        filename = re.sub(r'[^A-Za-z0-9._() -]', '_', filename)
        filename = re.sub(r'\.{2,}', '.', filename).strip(' .')
        if not filename:
            raise ValueError('A safe filename is required.')
        return filename[:180]

    @staticmethod
    def safe_relative_path(destination_path):
        raw = str(destination_path or '').replace('\\', '/')
        path = PurePosixPath(raw.lstrip('/'))
        if not raw or any(part in ('', '.', '..') for part in path.parts):
            raise ValueError('Unsafe storage path.')
        normalized = '/'.join(path.parts)
        if len(normalized) > 500:
            raise ValueError('Storage path is too long.')
        return normalized

    @staticmethod
    def object_name(prefix, extension=''):
        prefix = StorageDriver.safe_relative_path(prefix)
        suffix = str(extension or '')
        if suffix and not suffix.startswith('.'):
            suffix = '.' + suffix
        return f'{prefix}/{secrets.token_hex(24)}{suffix}'

    @staticmethod
    def _supabase_config():
        url = current_app.config.get('SUPABASE_URL')
        key = current_app.config.get('SUPABASE_SERVICE_ROLE_KEY')
        bucket = current_app.config.get('SUPABASE_STORAGE_BUCKET')
        if not url or not key or not bucket:
            raise RuntimeError('Private Supabase storage configuration is missing.')
        if not current_app.config.get('SUPABASE_STORAGE_PRIVATE', True):
            raise RuntimeError('Private Supabase storage is required.')
        return url.rstrip('/'), key, bucket

    @staticmethod
    def _supabase_headers(key, mime_type=None):
        headers = {'Authorization': f'Bearer {key}', 'apikey': key}
        if mime_type:
            headers['Content-Type'] = mime_type
        return headers

    @staticmethod
    def upload_file(file_bytes, destination_path, mime_type='application/octet-stream'):
        if file_bytes is None:
            raise ValueError('File content is required.')
        max_size = current_app.config.get('MAX_DOCUMENT_SIZE', 10 * 1024 * 1024)
        if len(file_bytes) > max_size:
            raise ValueError(f'Document exceeds the {max_size // (1024 * 1024)} MB limit.')
        destination_path = StorageDriver.safe_relative_path(destination_path)

        supabase_url = current_app.config.get('SUPABASE_URL')
        supabase_key = current_app.config.get('SUPABASE_SERVICE_ROLE_KEY')
        bucket = current_app.config.get('SUPABASE_STORAGE_BUCKET')
        if supabase_url and supabase_key and bucket:
            if not current_app.config.get('SUPABASE_STORAGE_PRIVATE', True):
                raise RuntimeError('Private Supabase storage is required.')
            endpoint = f"{supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{destination_path}"
            headers = StorageDriver._supabase_headers(supabase_key, mime_type)
            headers['x-upsert'] = 'false'
            try:
                response = requests.post(endpoint, data=file_bytes, headers=headers, timeout=20)
                if response.status_code in (200, 201):
                    return ('SUPABASE', destination_path)
                if response.status_code == 409:
                    raise ValueError('Storage object already exists; overwrite is forbidden.')
                raise RuntimeError(f'Supabase Storage upload rejected ({response.status_code}).')
            except requests.RequestException as exc:
                if current_app.config.get('APP_ENV') == 'production':
                    raise RuntimeError('Secure object storage is unavailable.') from exc
                current_app.logger.warning('Supabase Storage unavailable outside production: %s', exc)

        if current_app.config.get('APP_ENV') == 'production':
            raise RuntimeError('Production requires configured private Supabase object storage.')

        local_base = Path(current_app.config.get('UPLOAD_FOLDER')).resolve()
        full_path = (local_base / destination_path).resolve()
        if local_base not in full_path.parents:
            raise ValueError('Unsafe local storage path.')
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if full_path.exists():
            raise ValueError('Storage object already exists; overwrite is forbidden.')
        full_path.write_bytes(file_bytes)
        return ('LOCAL', destination_path)

    @staticmethod
    def get_file(storage_provider, storage_path):
        storage_path = StorageDriver.safe_relative_path(storage_path)
        if storage_provider == 'SUPABASE':
            url, key, bucket = StorageDriver._supabase_config()
            endpoint = f"{url}/storage/v1/object/{bucket}/{storage_path}"
            try:
                response = requests.get(
                    endpoint,
                    headers=StorageDriver._supabase_headers(key),
                    timeout=20,
                )
                if response.status_code == 200:
                    return response.content
            except requests.RequestException as exc:
                current_app.logger.warning('Supabase Storage download failed: %s', exc)
            return None

        if storage_provider != 'LOCAL':
            raise ValueError('Unsupported storage provider.')
        base = Path(current_app.config.get('UPLOAD_FOLDER')).resolve()
        full = (base / storage_path).resolve()
        if base not in full.parents or not full.is_file():
            return None
        return full.read_bytes()

    @staticmethod
    def create_signed_url(storage_provider, storage_path, expires_in=300):
        """Create a short-lived private URL without ever exposing the service-role key."""
        storage_path = StorageDriver.safe_relative_path(storage_path)
        try:
            expires_in = int(expires_in)
        except (TypeError, ValueError):
            raise ValueError('Signed URL expiry must be an integer.')
        if not 60 <= expires_in <= 900:
            raise ValueError('Signed URL expiry must be between 60 and 900 seconds.')

        if storage_provider != 'SUPABASE':
            raise ValueError('Signed URLs are only supported for Supabase storage.')

        url, key, bucket = StorageDriver._supabase_config()
        endpoint = f"{url}/storage/v1/object/sign/{bucket}/{storage_path}"
        try:
            response = requests.post(
                endpoint,
                json={'expiresIn': expires_in},
                headers=StorageDriver._supabase_headers(key, 'application/json'),
                timeout=10,
            )
        except requests.RequestException as exc:
            raise RuntimeError('Secure signed URL service is unavailable.') from exc

        if response.status_code not in (200, 201):
            raise RuntimeError(f'Supabase signed URL request rejected ({response.status_code}).')
        try:
            signed_path = response.json().get('signedURL') or response.json().get('signedUrl')
        except ValueError as exc:
            raise RuntimeError('Supabase returned an invalid signed URL response.') from exc
        if not signed_path or not isinstance(signed_path, str):
            raise RuntimeError('Supabase returned no signed URL.')
        if signed_path.startswith('/'):
            return f'{url}{signed_path}'
        if signed_path.startswith(url + '/'):
            return signed_path
        raise RuntimeError('Supabase returned an unexpected signed URL host.')

    @staticmethod
    def object_exists(storage_provider, storage_path):
        """Check whether the exact controlled object exists without downloading it."""
        storage_path = StorageDriver.safe_relative_path(storage_path)
        if storage_provider == 'SUPABASE':
            url, key, bucket = StorageDriver._supabase_config()
            endpoint = f"{url}/storage/v1/object/{bucket}/{storage_path}"
            try:
                response = requests.head(
                    endpoint,
                    headers=StorageDriver._supabase_headers(key),
                    timeout=10,
                )
            except requests.RequestException as exc:
                raise RuntimeError('Secure object storage availability check failed.') from exc
            if response.status_code == 200:
                return True
            if response.status_code == 404:
                return False
            raise RuntimeError(f'Supabase Storage availability check rejected ({response.status_code}).')

        if storage_provider != 'LOCAL':
            raise ValueError('Unsupported storage provider.')
        base = Path(current_app.config.get('UPLOAD_FOLDER')).resolve()
        full = (base / storage_path).resolve()
        if base not in full.parents:
            raise ValueError('Unsafe local storage path.')
        return full.is_file()

    @staticmethod
    def delete_file(storage_provider, storage_path):
        """Delete exactly one controlled object; callers must perform authorization first."""
        storage_path = StorageDriver.safe_relative_path(storage_path)
        if storage_provider == 'SUPABASE':
            url, key, bucket = StorageDriver._supabase_config()
            endpoint = f"{url}/storage/v1/object/{bucket}/{storage_path}"
            try:
                response = requests.delete(
                    endpoint,
                    headers=StorageDriver._supabase_headers(key),
                    timeout=20,
                )
                if response.status_code in (200, 204):
                    return True
                if response.status_code == 404:
                    return False
                raise RuntimeError(f'Supabase Storage deletion rejected ({response.status_code}).')
            except requests.RequestException as exc:
                raise RuntimeError('Secure object storage deletion failed.') from exc

        if storage_provider != 'LOCAL':
            raise ValueError('Unsupported storage provider.')
        base = Path(current_app.config.get('UPLOAD_FOLDER')).resolve()
        full = (base / storage_path).resolve()
        if base not in full.parents:
            raise ValueError('Unsafe local storage path.')
        if not full.is_file():
            return False
        full.unlink()
        return True
