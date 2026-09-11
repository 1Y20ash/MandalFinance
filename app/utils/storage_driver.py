import os
import re
import secrets
from pathlib import Path, PurePosixPath

import requests
from flask import current_app


class StorageDriver:
    """Secure storage abstraction for private financial evidence."""

    ALLOWED_TYPES = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.csv': 'text/csv',
        '.zip': 'application/zip',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.heic': 'image/heic',
        '.heif': 'image/heif',
        '.avif': 'image/avif',
    }

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
        if not raw or raw.startswith('/') or ':' in raw:
            raise ValueError('Unsafe storage path.')
        path = PurePosixPath(raw)
        if any(part in ('', '.', '..') for part in path.parts):
            raise ValueError('Unsafe storage path.')
        return '/'.join(path.parts)

    @classmethod
    def validate_document(cls, file_bytes, filename, mime_type):
        if file_bytes is None:
            raise ValueError('File content is required.')
        safe_name = cls.sanitize_filename(filename)
        mime = (mime_type or 'application/octet-stream').lower().split(';')[0].strip()
        suffix = Path(safe_name).suffix.lower()
        expected_mime = cls.ALLOWED_TYPES.get(suffix)
        if expected_mime is None:
            raise ValueError(f'Unsupported document extension: {suffix or "none"}.')
        if mime != expected_mime:
            raise ValueError('Document extension does not match its MIME type.')

        signatures = {
            'application/pdf': lambda data: data.startswith(b'%PDF-'),
            'image/png': lambda data: data.startswith(b'\x89PNG\r\n\x1a\n'),
            'image/jpeg': lambda data: data.startswith(b'\xff\xd8\xff'),
            'image/gif': lambda data: data.startswith((b'GIF87a', b'GIF89a')),
            'image/webp': lambda data: len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP',
            'image/heic': lambda data: cls._is_heif_container(data),
            'image/heif': lambda data: cls._is_heif_container(data),
            'image/avif': lambda data: cls._is_heif_container(data),
            'application/zip': lambda data: data.startswith((b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08')),
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': lambda data: data.startswith(b'PK'),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': lambda data: data.startswith(b'PK'),
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': lambda data: data.startswith(b'PK'),
        }
        checker = signatures.get(mime)
        if checker and not checker(file_bytes):
            raise ValueError('Document content does not match the declared file type.')
        return safe_name, mime

    @staticmethod
    def _is_heif_container(data):
        if len(data) < 12 or data[4:8] != b'ftyp':
            return False
        compatible_brands = data[8:64]
        return any(brand in compatible_brands for brand in (
            b'heic', b'heix', b'hevc', b'hevx', b'heim', b'heis', b'hevm', b'hevs', b'mif1', b'msf1', b'avif', b'avis'
        ))

    @staticmethod
    def generate_object_token(length=32):
        return secrets.token_urlsafe(length)

    @staticmethod
    def upload_file(file_bytes, destination_path, mime_type='application/octet-stream'):
        if file_bytes is None:
            raise ValueError('File content is required.')
        max_size = current_app.config.get('MAX_DOCUMENT_SIZE', 10 * 1024 * 1024)
        if len(file_bytes) > max_size:
            raise ValueError(f'Document exceeds the {max_size // (1024 * 1024)} MB limit.')
        destination_path = StorageDriver.safe_relative_path(destination_path)
        supabase_url = (current_app.config.get('SUPABASE_URL') or '').strip().rstrip('/')
        supabase_key = (current_app.config.get('SUPABASE_SERVICE_ROLE_KEY') or '').strip()
        bucket = (current_app.config.get('SUPABASE_STORAGE_BUCKET') or '').strip()
        if supabase_url and supabase_key:
            if not bucket:
                raise RuntimeError('Private object storage bucket is not configured.')
            endpoint = f"{supabase_url}/storage/v1/object/{bucket}/{destination_path}"
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
                if response.status_code in (400, 409):
                    raise ValueError('Storage object already exists or was rejected by storage policy.')
                if response.status_code in (401, 403):
                    raise RuntimeError('Secure object storage rejected the configured credentials or policy.')
                if response.status_code == 413:
                    raise ValueError('The storage provider rejected the document because it exceeds its size limit.')
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
    def delete_file(storage_provider, storage_path):
        storage_path = StorageDriver.safe_relative_path(storage_path)
        if storage_provider == 'SUPABASE':
            url = (current_app.config.get('SUPABASE_URL') or '').strip().rstrip('/')
            key = (current_app.config.get('SUPABASE_SERVICE_ROLE_KEY') or '').strip()
            bucket = (current_app.config.get('SUPABASE_STORAGE_BUCKET') or '').strip()
            if not url or not key or not bucket:
                return False
            endpoint = f"{url}/storage/v1/object/{bucket}/{storage_path}"
            try:
                response = requests.delete(endpoint, headers={'Authorization': f'Bearer {key}', 'apikey': key}, timeout=20)
                return response.status_code in (200, 204)
            except requests.RequestException:
                return False
        base = Path(current_app.config.get('UPLOAD_FOLDER')).resolve()
        full = (base / storage_path).resolve()
        if base not in full.parents:
            raise ValueError('Unsafe local storage path.')
        if full.is_file():
            full.unlink()
            return True
        return False

    @staticmethod
    def get_file(storage_provider, storage_path):
        storage_path = StorageDriver.safe_relative_path(storage_path)
        if storage_provider == 'SUPABASE':
            url = (current_app.config.get('SUPABASE_URL') or '').strip().rstrip('/')
            key = (current_app.config.get('SUPABASE_SERVICE_ROLE_KEY') or '').strip()
            bucket = (current_app.config.get('SUPABASE_STORAGE_BUCKET') or '').strip()
            if not url or not key or not bucket:
                raise RuntimeError('Supabase storage configuration is missing.')
            endpoint = f"{url}/storage/v1/object/{bucket}/{storage_path}"
            try:
                response = requests.get(endpoint, headers={'Authorization': f'Bearer {key}', 'apikey': key}, timeout=20)
                if response.status_code == 200:
                    return response.content
            except requests.RequestException as exc:
                current_app.logger.warning('Supabase Storage download failed: %s', exc)
            return None
        base = Path(current_app.config.get('UPLOAD_FOLDER')).resolve()
        full = (base / storage_path).resolve()
        if base not in full.parents or not full.is_file():
            return None
        return full.read_bytes()
