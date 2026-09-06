from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from app.models.document import Document, EvidencePack
from app.services.document_service import DocumentService
from app.utils.storage_driver import StorageDriver
from app.utils.decorators import permission_required

documents_bp = Blueprint('documents', __name__, url_prefix='/documents')

@documents_bp.route('/')
@login_required
@permission_required('document.view')
def list_documents():
    page = request.args.get('page', 1, type=int)
    category_filter = request.args.get('category', '').strip()
    entity_type = request.args.get('entity_type', '').strip()

    query = Document.query.filter_by(is_archived=False)
    if category_filter:
        query = query.filter_by(category=category_filter)
    if entity_type:
        query = query.filter_by(entity_type=entity_type)

    pagination = query.order_by(Document.created_at.desc()).paginate(page=page, per_page=15)
    return render_template('documents/list.html', pagination=pagination, category_filter=category_filter, entity_type=entity_type)


@documents_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@permission_required('document.upload')
def upload_document():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        entity_type = request.form.get('entity_type', 'GENERAL').strip()
        entity_id = request.form.get('entity_id', type=int)
        description = request.form.get('description', '').strip()

        file = request.files.get('file')
        if not file or not file.filename:
            flash('Please select a valid file to upload.', 'warning')
            return redirect(url_for('documents.upload_document'))

        file_bytes = file.read()
        filename = file.filename
        file_type = file.mimetype or 'application/octet-stream'

        try:
            doc = DocumentService.upload_document(
                file_bytes=file_bytes,
                filename=filename,
                file_type=file_type,
                category=category,
                title=title,
                entity_type=entity_type,
                uploader_user=current_user,
                entity_id=entity_id,
                description=description
            )
            flash(f'Document "{doc.title}" uploaded successfully with SHA-256 verification.', 'success')
            return redirect(url_for('documents.view_document', doc_id=doc.id))
        except Exception as e:
            flash(f'Upload failed: {str(e)}', 'danger')

    entity_type_arg = request.args.get('entity_type', 'GENERAL')
    entity_id_arg = request.args.get('entity_id', type=int)
    return render_template('documents/upload.html', entity_type=entity_type_arg, entity_id=entity_id_arg)


@documents_bp.route('/<int:doc_id>')
@login_required
@permission_required('document.view')
def view_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    return render_template('documents/view.html', doc=doc)


@documents_bp.route('/<int:doc_id>/download')
@login_required
@permission_required('document.download')
def download_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    file_bytes = StorageDriver.get_file(doc.storage_provider, doc.storage_path)

    if not file_bytes:
        flash('Requested document file could not be retrieved from storage.', 'danger')
        return redirect(url_for('documents.view_document', doc_id=doc.id))

    response = make_response(file_bytes)
    response.headers['Content-Type'] = doc.file_type
    response.headers['Content-Disposition'] = f'inline; filename="{doc.original_filename}"'
    return response


@documents_bp.route('/<int:doc_id>/replace', methods=['POST'])
@login_required
@permission_required('document.replace')
def replace_document(doc_id):
    reason = request.form.get('replacement_reason', '').strip()
    file = request.files.get('file')

    if not reason or not file or not file.filename:
        flash('File and replacement reason are required.', 'warning')
        return redirect(url_for('documents.view_document', doc_id=doc_id))

    file_bytes = file.read()
    try:
        doc = DocumentService.replace_document(
            document_id=doc_id,
            new_file_bytes=file_bytes,
            new_filename=file.filename,
            new_file_type=file.mimetype or 'application/octet-stream',
            uploader_user=current_user,
            replacement_reason=reason
        )
        flash(f'Document replaced successfully. Version updated to v{doc.current_version_number}.', 'success')
    except Exception as e:
        flash(f'Document replacement failed: {str(e)}', 'danger')

    return redirect(url_for('documents.view_document', doc_id=doc_id))


@documents_bp.route('/<int:doc_id>/verify')
@login_required
@permission_required('document.verify')
def verify_document(doc_id):
    try:
        is_match, recorded_hash, computed_hash = DocumentService.verify_document_integrity(doc_id)
        if is_match:
            flash(f'✓ SHA-256 Digital Integrity Verified! Hash matches: {computed_hash[:16]}...', 'success')
        else:
            flash(f'⚠ WARNING: File content differs from recorded hash! Recorded: {recorded_hash[:16]}..., Computed: {computed_hash[:16]}...', 'danger')
    except Exception as e:
        flash(f'Integrity verification failed: {str(e)}', 'danger')

    return redirect(url_for('documents.view_document', doc_id=doc_id))


@documents_bp.route('/evidence-pack/<entity_type>/<int:entity_id>')
@login_required
@permission_required('evidence_pack.create')
def generate_evidence_pack(entity_type, entity_id):
    try:
        pack, zip_bytes = DocumentService.generate_evidence_pack(entity_type, entity_id, current_user)
        response = make_response(zip_bytes)
        response.headers['Content-Type'] = 'application/zip'
        response.headers['Content-Disposition'] = f'attachment; filename="EvidencePack_{pack.pack_ref}.zip"'
        return response
    except Exception as e:
        flash(f'Evidence Pack generation failed: {str(e)}', 'danger')
        return redirect(url_for('documents.list_documents'))
