import os
import requests
from pathlib import Path
from flask import current_app

class StorageDriver:
    @staticmethod
    def upload_file(file_bytes, destination_path, mime_type="application/octet-stream"):
        """
        Uploads a file to Supabase Storage if configured; otherwise saves to local UPLOAD_FOLDER.
        Returns tuple: (storage_provider, storage_path)
        """
        supabase_url = current_app.config.get('SUPABASE_URL')
        supabase_key = current_app.config.get('SUPABASE_SERVICE_ROLE_KEY')
        bucket = current_app.config.get('SUPABASE_STORAGE_BUCKET', 'mandal-financial-documents')

        if supabase_url and supabase_key:
            # Use Supabase Storage REST API
            endpoint = f"{supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{destination_path.lstrip('/')}"
            headers = {
                "Authorization": f"Bearer {supabase_key}",
                "apikey": supabase_key,
                "Content-Type": mime_type,
                "x-upsert": "true"
            }
            try:
                response = requests.post(endpoint, data=file_bytes, headers=headers, timeout=10)
                if response.status_code in (200, 201):
                    return ('SUPABASE', destination_path)
            except Exception as e:
                current_app.logger.warning(f"Supabase Storage upload failed, falling back to local: {e}")

        # Local storage fallback
        local_base = Path(current_app.config.get('UPLOAD_FOLDER'))
        full_path = local_base / destination_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'wb') as f:
            f.write(file_bytes)
            
        return ('LOCAL', str(destination_path))

    @staticmethod
    def get_file(storage_provider, storage_path):
        """
        Retrieves raw file bytes from Supabase Storage or local storage.
        """
        if storage_provider == 'SUPABASE':
            supabase_url = current_app.config.get('SUPABASE_URL')
            supabase_key = current_app.config.get('SUPABASE_SERVICE_ROLE_KEY')
            bucket = current_app.config.get('SUPABASE_STORAGE_BUCKET', 'mandal-financial-documents')
            
            endpoint = f"{supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{storage_path.lstrip('/')}"
            headers = {
                "Authorization": f"Bearer {supabase_key}",
                "apikey": supabase_key
            }
            try:
                response = requests.get(endpoint, headers=headers, timeout=10)
                if response.status_code == 200:
                    return response.content
            except Exception as e:
                current_app.logger.warning(f"Supabase Storage download failed: {e}")

        # Fallback local
        local_base = Path(current_app.config.get('UPLOAD_FOLDER'))
        full_path = local_base / storage_path
        if full_path.exists():
            with open(full_path, 'rb') as f:
                return f.read()
        return None
