from datetime import datetime
from app.extensions import db

class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    doc_ref = db.Column(db.String(50), unique=True, nullable=False, index=True)  # DOC-YYYY-XXXX
    
    category = db.Column(db.String(50), nullable=False)  # 'BILL', 'INVOICE', 'RECEIPT', 'PAYMENT_PROOF', 'DONATION_PROOF', 'BANK_STATEMENT', 'QUOTATION', 'AGREEMENT', 'PHOTO', 'OTHER'
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Linked entity metadata
    entity_type = db.Column(db.String(30), nullable=False)  # 'EXPENSE', 'DONATION', 'SPONSORSHIP', 'MEMBER', 'VENDOR', 'RECONCILIATION', 'GENERAL'
    entity_id = db.Column(db.Integer, nullable=True)
    
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(100), nullable=False)  # MIME type e.g. application/pdf, image/jpeg
    file_size = db.Column(db.Integer, nullable=False)  # size in bytes
    
    current_version_number = db.Column(db.Integer, nullable=False, default=1)
    current_sha256_hash = db.Column(db.String(64), nullable=False)  # SHA-256 hex string
    storage_provider = db.Column(db.String(30), nullable=False, default='SUPABASE')  # 'SUPABASE' or 'LOCAL'
    storage_path = db.Column(db.String(500), nullable=False)
    
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_verified = db.Column(db.Boolean, default=True)
    is_archived = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id])
    versions = db.relationship('DocumentVersion', backref='document', lazy=True, cascade='all, delete-orphan', order_by='DocumentVersion.version_number.desc()')

    def __repr__(self):
        return f'<Document {self.doc_ref} - {self.title} (v{self.current_version_number})>'


class DocumentVersion(db.Model):
    __tablename__ = 'document_versions'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    
    sha256_hash = db.Column(db.String(64), nullable=False)
    storage_provider = db.Column(db.String(30), nullable=False, default='SUPABASE')
    storage_path = db.Column(db.String(500), nullable=False)
    
    replacement_reason = db.Column(db.Text, nullable=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploaded_by = db.relationship('User', foreign_keys=[uploaded_by_id])


class EvidencePack(db.Model):
    __tablename__ = 'evidence_packs'

    id = db.Column(db.Integer, primary_key=True)
    pack_ref = db.Column(db.String(50), unique=True, nullable=False, index=True)  # EVP-YYYY-XXXX
    title = db.Column(db.String(150), nullable=False)
    entity_type = db.Column(db.String(30), nullable=False)  # 'EXPENSE', 'EVENT', 'DONATION', 'FULL_YEAR'
    entity_id = db.Column(db.Integer, nullable=True)
    
    zip_storage_path = db.Column(db.String(500), nullable=True)
    pdf_summary_path = db.Column(db.String(500), nullable=True)
    sha256_hash = db.Column(db.String(64), nullable=True)
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    created_by = db.relationship('User', foreign_keys=[created_by_id])
