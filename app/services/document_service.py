import datetime
import io
import uuid
import zipfile

from app.extensions import db
from app.models.document import Document, DocumentVersion, EvidencePack
from app.utils.hash_utils import compute_sha256
from app.utils.storage_driver import StorageDriver
from app.services.audit_service import AuditService


class DocumentService:
    @staticmethod
    def _generate_doc_ref():
        return f"DOC-{datetime.datetime.utcnow().year}-{uuid.uuid4().hex[:12].upper()}"

    @staticmethod
    def _generate_pack_ref():
        return f"EVP-{datetime.datetime.utcnow().year}-{uuid.uuid4().hex[:12].upper()}"

    @staticmethod
    def upload_document(file_bytes, filename, file_type, category, title, entity_type, uploader_user, entity_id=None, description=None):
        sha256_hash = compute_sha256(file_bytes)
        file_size = len(file_bytes)
        doc_ref = DocumentService._generate_doc_ref()
        destination_path = f"documents/{entity_type.lower()}/{doc_ref}/v1_{StorageDriver.sanitize_filename(filename)}"
        provider, storage_path = StorageDriver.upload_file(file_bytes, destination_path, mime_type=file_type)
        try:
            doc = Document(
                doc_ref=doc_ref, category=category, title=title, description=description,
                entity_type=entity_type, entity_id=entity_id, original_filename=filename,
                file_type=file_type, file_size=file_size, current_version_number=1,
                current_sha256_hash=sha256_hash, storage_provider=provider,
                storage_path=storage_path, uploaded_by_id=uploader_user.id,
            )
            db.session.add(doc)
            db.session.flush()
            db.session.add(DocumentVersion(
                document_id=doc.id, version_number=1, original_filename=filename,
                file_type=file_type, file_size=file_size, sha256_hash=sha256_hash,
                storage_provider=provider, storage_path=storage_path,
                replacement_reason='Initial upload', uploaded_by_id=uploader_user.id,
            ))
            AuditService.log_action(
                'UPLOAD', 'DOCUMENT', doc.id,
                f"Uploaded document {doc_ref} ('{title}') with SHA-256 {sha256_hash[:10]}...",
                commit=False,
            )
            db.session.commit()
            return doc
        except Exception:
            db.session.rollback()
            try:
                StorageDriver.delete_file(provider, storage_path)
            except Exception:
                current_app = __import__('flask').current_app
                current_app.logger.exception('Failed to clean up orphaned document object %s', storage_path)
            raise

    @staticmethod
    def replace_document(document_id, new_file_bytes, new_filename, new_file_type, uploader_user, replacement_reason):
        doc = db.session.get(Document, document_id)
        if not doc:
            raise ValueError('Document not found.')
        sha256_hash = compute_sha256(new_file_bytes)
        next_version = doc.current_version_number + 1
        destination_path = f"documents/{doc.entity_type.lower()}/{doc.doc_ref}/v{next_version}_{StorageDriver.sanitize_filename(new_filename)}"
        provider, storage_path = StorageDriver.upload_file(new_file_bytes, destination_path, mime_type=new_file_type)
        try:
            doc.current_version_number = next_version
            doc.current_sha256_hash = sha256_hash
            doc.original_filename = new_filename
            doc.file_type = new_file_type
            doc.file_size = len(new_file_bytes)
            doc.storage_provider = provider
            doc.storage_path = storage_path
            db.session.add(DocumentVersion(
                document_id=doc.id, version_number=next_version,
                original_filename=new_filename, file_type=new_file_type,
                file_size=len(new_file_bytes), sha256_hash=sha256_hash,
                storage_provider=provider, storage_path=storage_path,
                replacement_reason=replacement_reason, uploaded_by_id=uploader_user.id,
            ))
            AuditService.log_action(
                'REPLACE', 'DOCUMENT', doc.id,
                f"Replaced document {doc.doc_ref} creating version v{next_version}. Reason: {replacement_reason}",
                commit=False,
            )
            db.session.commit()
            return doc
        except Exception:
            db.session.rollback()
            try:
                StorageDriver.delete_file(provider, storage_path)
            except Exception:
                from flask import current_app
                current_app.logger.exception('Failed to clean up orphaned replacement object %s', storage_path)
            raise

    @staticmethod
    def verify_document_integrity(document_id):
        doc = db.session.get(Document, document_id)
        if not doc:
            raise ValueError('Document not found.')
        file_bytes = StorageDriver.get_file(doc.storage_provider, doc.storage_path)
        if not file_bytes:
            return (False, doc.current_sha256_hash, 'FILE_NOT_FOUND')
        computed_hash = compute_sha256(file_bytes)
        is_match = computed_hash == doc.current_sha256_hash
        doc.is_verified = is_match
        AuditService.log_action(
            'VERIFY', 'DOCUMENT', doc.id,
            f"Verified integrity for {doc.doc_ref}: {'MATCH' if is_match else 'MISMATCH'}",
            commit=False,
        )
        db.session.commit()
        return (is_match, doc.current_sha256_hash, computed_hash)

    @staticmethod
    def generate_evidence_pack(entity_type, entity_id, user):
        docs = Document.query.filter_by(entity_type=entity_type, entity_id=entity_id, is_archived=False).all()
        pack_ref = DocumentService._generate_pack_ref()
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            manifest_lines = [
                '============================================================',
                'SHREE ASHTAVINAYAK GANESH UTSAV MANDAL - FINANCIAL EVIDENCE PACK',
                f'Pack Reference: {pack_ref}',
                f'Entity Type: {entity_type} | Entity ID: {entity_id}',
                f'Generated At: {datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}',
                '============================================================\n',
                'DOCUMENT PROOFS INCLUDED:\n',
            ]
            for d in docs:
                file_bytes = StorageDriver.get_file(d.storage_provider, d.storage_path)
                if file_bytes:
                    safe_name = StorageDriver.sanitize_filename(d.original_filename)
                    zf.writestr(f'proofs/{d.doc_ref}_v{d.current_version_number}_{safe_name}', file_bytes)
                    manifest_lines.append(f'- {d.doc_ref} | {d.title} | Category: {d.category} | SHA-256: {d.current_sha256_hash}')
            zf.writestr('MANIFEST.txt', '\n'.join(manifest_lines))

        zip_bytes = zip_buffer.getvalue()
        pack_hash = compute_sha256(zip_bytes)
        pack_path = f'evidence_packs/{pack_ref}.zip'
        provider, storage_path = StorageDriver.upload_file(zip_bytes, pack_path, mime_type='application/zip')
        try:
            pack = EvidencePack(
                pack_ref=pack_ref, title=f'Evidence Pack for {entity_type} #{entity_id}',
                entity_type=entity_type, entity_id=entity_id, zip_storage_path=storage_path,
                sha256_hash=pack_hash, created_by_id=user.id,
            )
            db.session.add(pack)
            db.session.flush()
            AuditService.log_action(
                'CREATE', 'EVIDENCE_PACK', pack.id,
                f'Generated Evidence Pack {pack_ref} with {len(docs)} document proofs',
                commit=False,
            )
            db.session.commit()
            return pack, zip_bytes
        except Exception:
            db.session.rollback()
            try:
                StorageDriver.delete_file(provider, storage_path)
            except Exception:
                from flask import current_app
                current_app.logger.exception('Failed to clean up orphaned evidence pack %s', storage_path)
            raise
