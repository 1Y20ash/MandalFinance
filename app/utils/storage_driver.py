import os
import re
from pathlib import Path, PurePosixPath
from flask import current_app
import requests


class StorageDriver:
    ALLOWED_MIME_PREFIXES = ('application/', 'image/', 'text/', 'audio/', 'video/')

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
        return '/'.join(path.parts)

    @staticmethod
    def _supabase_config():
        return (
            current_app.config.get('SUPABASE_URL'),
            current_app.config.get('SUPABASE_SERVICE_ROLE_KEY'),
            current_app.config.get('SUPABASE_STORAGE_BUCKET', 'mandal-financial-documents'),
        )

    @staticmethod
    def upload_file(file_bytes, destination_path, mime_type='application/octet-stream'):
        if file_bytes is None:
            raise ValueError('File content is required.')
        max_size = current_app.config.get('MAX_DOCUMENT_SIZE', 10 * 1024 * 1024)
        if len(file_bytes) > max_size:
            raise ValueError(f'Document exceeds the {max_size // (1024 * 1024)} MB limit.')
        destination_path = StorageDriver.safe_relative_path(destination_path)
        supabase_url, supabase_key, bucket = StorageDriver._supabase_config()
        if supabase_url and supabase_key:
            endpoint = f"{supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{destination_path}"
            headers = {
                'Authorization': f'Bearer {supabase_key}',
                'apikey': supabase_key,
                'Content-Type': mime_type,
                'x-upsert': 'false',
            }
            try:
                response = requests.post(endpoint, data=file_bytes, headers=headers, timeout=20)
                if response.status_code in (200, 201):
                    return ('SUPABASE', destination_path)
                if response.status_code == 409:
                    raise ValueError('Storage object already exists; overwrite is forbidden.')
                raise RuntimeError(f'Supabase Storage upload rejected ({response.status_code}).')
            except requests.RequestException as exc:
                if current_app.config.get('ENV') == 'production' or not current_app.config.get('TESTING'):
                    if current_app.config.get('SUPABASE_URL'):
                        raise RuntimeError('Secure object storage is unavailable.') from exc
                current_app.logger.warning('Supabase Storage unavailable; using local storage only outside production: %s', exc)

        if current_app.config.get('ENV') == 'production':
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
            supabase_url, supabase_key, bucket = StorageDriver._supabase_config()
            if not supabase_url or not supabase_key:
                raise RuntimeError('Supabase storage configuration is missing.')
            endpoint = f"{supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{storage_path}"
            headers = {'Authorization': f'Bearer {supabase_key}', 'apikey': supabase_key}
            try:
                response = requests.get(endpoint, headers=headers, timeout=20)
                if response.status_code == 200:
                    return response.content
            except requests.RequestException as exc:
                current_app.logger.warning('Supabase Storage download failed: %s', exc)
            return None
        local_base = Path(current_app.config.get('UPLOAD_FOLDER')).resolve()
        full_path = (local_base / storage_path).resolve()
        if local_base not in full_path.parents or not full_path.is_file():
            return None
        return full_path.read_bytes()
