import datetime
import io
import secrets
import zipfile
from app.extensions import db
from app.models.document import Document, DocumentVersion, EvidencePack
from app.utils.hash_utils import compute_sha256
from app.utils.storage_driver import StorageDriver
from app.services.audit_service import AuditService


class DocumentService:
    @staticmethod
    def _generate_doc_ref():
        year = datetime.datetime.utcnow().year
        # Random suffix avoids predictable object references and count races.
        return f"DOC-{year}-{secrets.token_hex(4).upper()}"

    @staticmethod
    def _generate_pack_ref():
        year = datetime.datetime.utcnow().year
        return f"EVP-{year}-{secrets.token_hex(4).upper()}"

    @staticmethod
    def _object_path(entity_type, doc_ref, version_number, filename):
        safe_entity = ''.join(ch for ch in str(entity_type).lower() if ch.isalnum() or ch in ('_', '-'))[:30]
        extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        return StorageDriver.object_name(
            f'documents/{safe_entity or "general"}/{doc_ref}/v{version_number}',
            extension,
        )

    @staticmethod
    def upload_document(file_bytes, filename, file_type, category, title, entity_type, uploader_user,
                        entity_id=None, description=None):
        if not uploader_user or not getattr(uploader_user, 'id', None):
            raise ValueError('A valid authenticated uploader is required.')
        filename = StorageDriver.sanitize_filename(filename)
        sha256_hash = compute_sha256(file_bytes)
        file_size = len(file_bytes)
        doc_ref = DocumentService._generate_doc_ref()
        destination_path = DocumentService._object_path(entity_type, doc_ref, 1, filename)
        provider, storage_path = StorageDriver.upload_file(file_bytes, destination_path, mime_type=file_type)

        try:
            doc = Document(
                doc_ref=doc_ref, category=category, title=title[:150], description=description,
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
                action='UPLOAD', entity_type='DOCUMENT', entity_id=doc.id,
                description=f'Uploaded document {doc_ref} with SHA-256 verification.', commit=False,
            )
            db.session.commit()
            return doc
        except Exception:
            db.session.rollback()
            try:
                StorageDriver.delete_file(provider, storage_path)
            except Exception:
                # The database transaction remains rolled back; cleanup can be retried by storage reconciliation.
                pass
            raise

    @staticmethod
    def replace_document(document_id, new_file_bytes, new_filename, new_file_type, uploader_user, replacement_reason):
        doc = db.session.get(Document, document_id)
        if not doc or doc.is_archived:
            raise ValueError('Document not found.')
        if not uploader_user or not getattr(uploader_user, 'id', None):
            raise ValueError('A valid authenticated uploader is required.')
        replacement_reason = replacement_reason.strip()
        if not replacement_reason:
            raise ValueError('Replacement reason is required.')

        new_filename = StorageDriver.sanitize_filename(new_filename)
        sha256_hash = compute_sha256(new_file_bytes)
        file_size = len(new_file_bytes)
        next_version = doc.current_version_number + 1
        destination_path = DocumentService._object_path(doc.entity_type, doc.doc_ref, next_version, new_filename)
        provider, storage_path = StorageDriver.upload_file(new_file_bytes, destination_path, mime_type=new_file_type)

        try:
            doc.current_version_number = next_version
            doc.current_sha256_hash = sha256_hash
            doc.original_filename = new_filename
            doc.file_type = new_file_type
            doc.file_size = file_size
            doc.storage_provider = provider
            doc.storage_path = storage_path
            doc.is_verified = True
            db.session.add(DocumentVersion(
                document_id=doc.id, version_number=next_version, original_filename=new_filename,
                file_type=new_file_type, file_size=file_size, sha256_hash=sha256_hash,
                storage_provider=provider, storage_path=storage_path,
                replacement_reason=replacement_reason[:1000], uploaded_by_id=uploader_user.id,
            ))
            AuditService.log_action(
                action='REPLACE', entity_type='DOCUMENT', entity_id=doc.id,
                description=f'Replaced document {doc.doc_ref} creating version v{next_version}.', commit=False,
            )
            db.session.commit()
            return doc
        except Exception:
            db.session.rollback()
            try:
                StorageDriver.delete_file(provider, storage_path)
            except Exception:
                pass
            raise

    @staticmethod
    def verify_document_integrity(document_id):
        doc = db.session.get(Document, document_id)
        if not doc or doc.is_archived:
            raise ValueError('Document not found.')
        file_bytes = StorageDriver.get_file(doc.storage_provider, doc.storage_path)
        if file_bytes is None:
            doc.is_verified = False
            db.session.commit()
            AuditService.log_action('VERIFY', 'DOCUMENT', doc.id,
                                    f'Integrity verification failed for {doc.doc_ref}: file unavailable.')
            return (False, doc.current_sha256_hash, 'FILE_NOT_FOUND')

        computed_hash = compute_sha256(file_bytes)
        is_match = computed_hash == doc.current_sha256_hash
        doc.is_verified = is_match
        db.session.commit()
        AuditService.log_action(
            'VERIFY', 'DOCUMENT', doc.id,
            f'Verified integrity for {doc.doc_ref}: {"MATCH" if is_match else "MISMATCH"}',
        )
        return (is_match, doc.current_sha256_hash, computed_hash)

    @staticmethod
    def generate_evidence_pack(entity_type, entity_id, user):
        if not user or not getattr(user, 'id', None):
            raise ValueError('A valid authenticated user is required.')
        docs = Document.query.filter_by(
            entity_type=entity_type.upper(), entity_id=entity_id, is_archived=False
        ).all()
        pack_ref = DocumentService._generate_pack_ref()
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            manifest_lines = [
                'SHREE ASHTAVINAYAK GANESH UTSAV MANDAL - FINANCIAL EVIDENCE PACK',
                f'Pack Reference: {pack_ref}',
                f'Entity Type: {entity_type.upper()} | Entity ID: {entity_id}',
                f'Generated At: {datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}',
                '', 'DOCUMENT PROOFS INCLUDED:',
            ]
            for d in docs:
                file_bytes = StorageDriver.get_file(d.storage_provider, d.storage_path)
                if file_bytes is None:
                    continue
                # Never allow stored filenames to create ZIP path traversal.
                safe_name = StorageDriver.sanitize_filename(d.original_filename)
                arcname = f'proofs/{d.doc_ref}_v{d.current_version_number}_{safe_name}'
                zf.writestr(arcname, file_bytes)
                manifest_lines.append(
                    f'- {d.doc_ref} | {d.title} | Category: {d.category} | SHA-256: {d.current_sha256_hash}'
                )
            zf.writestr('MANIFEST.txt', '\n'.join(manifest_lines))

        zip_buffer.seek(0)
        zip_bytes = zip_buffer.getvalue()
        pack_hash = compute_sha256(zip_bytes)
        pack_path = f'evidence_packs/{pack_ref}.zip'
        provider, storage_path = StorageDriver.upload_file(zip_bytes, pack_path, mime_type='application/zip')
        try:
            pack = EvidencePack(
                pack_ref=pack_ref, title=f'Evidence Pack for {entity_type.upper()} #{entity_id}',
                entity_type=entity_type.upper(), entity_id=entity_id,
                zip_storage_path=storage_path, sha256_hash=pack_hash, created_by_id=user.id,
            )
            db.session.add(pack)
            db.session.flush()
            AuditService.log_action('CREATE', 'EVIDENCE_PACK', pack.id,
                                    f'Generated Evidence Pack {pack_ref} with {len(docs)} document proofs.',
                                    commit=False)
            db.session.commit()
            return pack, zip_bytes
        except Exception:
            db.session.rollback()
            try:
                StorageDriver.delete_file(provider, storage_path)
            except Exception:
                pass
            raise
