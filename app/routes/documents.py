from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from app.models.document import Document
from app.services.document_service import DocumentService
from app.utils.storage_driver import StorageDriver
from app.utils.decorators import permission_required
from app.services.audit_service import AuditService

documents_bp = Blueprint('documents', __name__, url_prefix='/documents')

ALLOWED_MIME = {
    'application/pdf', 'text/plain', 'text/csv', 'application/zip',
    'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'image/jpeg', 'image/png', 'image/gif'
}


def _validated_upload(file):
    if not file or not file.filename: raise ValueError('Please select a valid file to upload.')
    filename = StorageDriver.sanitize_filename(file.filename)
    content = file.read()
    max_size = 10 * 1024 * 1024
    if len(content) > max_size: raise ValueError('Document exceeds the 10 MB financial evidence limit.')
    mime = (file.mimetype or 'application/octet-stream').lower().split(';')[0].strip()
    if mime not in ALLOWED_MIME: raise ValueError(f'Unsupported document type: {mime}.')
    return content, filename, mime


@documents_bp.route('/')
@login_required
@permission_required('document.view')
def list_documents():
    page=request.args.get('page',1,type=int);category_filter=request.args.get('category','').strip();entity_type=request.args.get('entity_type','').strip()
    query=Document.query.filter_by(is_archived=False)
    if category_filter:query=query.filter_by(category=category_filter)
    if entity_type:query=query.filter_by(entity_type=entity_type)
    pagination=query.order_by(Document.created_at.desc()).paginate(page=page,per_page=15)
    return render_template('documents/list.html',pagination=pagination,category_filter=category_filter,entity_type=entity_type)

@documents_bp.route('/upload',methods=['GET','POST'])
@login_required
@permission_required('document.upload')
def upload_document():
    if request.method=='POST':
        title=request.form.get('title','').strip();category=request.form.get('category','').strip();entity_type=request.form.get('entity_type','GENERAL').strip();entity_id=request.form.get('entity_id',type=int);description=request.form.get('description','').strip()
        try:
            content,filename,mime=_validated_upload(request.files.get('file'))
            if not title or not category: raise ValueError('Document title and category are required.')
            doc=DocumentService.upload_document(content,filename,mime,category,title,entity_type,current_user,entity_id,description)
            flash(f'Document "{doc.title}" uploaded successfully with SHA-256 verification.','success')
            return redirect(url_for('documents.view_document',doc_id=doc.id))
        except Exception as e: flash(f'Upload failed: {str(e)}','danger')
    return render_template('documents/upload.html',entity_type=request.args.get('entity_type','GENERAL'),entity_id=request.args.get('entity_id',type=int))

@documents_bp.route('/<int:doc_id>')
@login_required
@permission_required('document.view')
def view_document(doc_id): return render_template('documents/view.html',doc=Document.query.get_or_404(doc_id))

@documents_bp.route('/<int:doc_id>/download')
@login_required
@permission_required('document.download')
def download_document(doc_id):
    doc=Document.query.get_or_404(doc_id)
    try:file_bytes=StorageDriver.get_file(doc.storage_provider,doc.storage_path)
    except Exception as e: flash(str(e),'danger'); return redirect(url_for('documents.view_document',doc_id=doc.id))
    if not file_bytes: flash('Requested document file could not be retrieved from storage.','danger'); return redirect(url_for('documents.view_document',doc_id=doc.id))
    AuditService.log_action('DOWNLOAD','DOCUMENT',doc.id,f'Document {doc.doc_ref} downloaded by authorized user.',commit=True)
    response=make_response(file_bytes);response.headers['Content-Type']=doc.file_type;response.headers['Content-Disposition']=f'inline; filename="{StorageDriver.sanitize_filename(doc.original_filename)}"';response.headers['X-Content-Type-Options']='nosniff';return response

@documents_bp.route('/<int:doc_id>/replace',methods=['POST'])
@login_required
@permission_required('document.replace')
def replace_document(doc_id):
    reason=request.form.get('replacement_reason','').strip()
    try:
        content,filename,mime=_validated_upload(request.files.get('file'))
        if not reason: raise ValueError('Replacement reason is required.')
        doc=DocumentService.replace_document(doc_id,content,filename,mime,current_user,reason)
        flash(f'Document replaced successfully. Version updated to v{doc.current_version_number}.','success')
    except Exception as e: flash(f'Document replacement failed: {str(e)}','danger')
    return redirect(url_for('documents.view_document',doc_id=doc_id))

@documents_bp.route('/<int:doc_id>/verify')
@login_required
@permission_required('document.verify')
def verify_document(doc_id):
    try:
        ok,recorded,computed=DocumentService.verify_document_integrity(doc_id)
        flash(f'✓ SHA-256 integrity verified: {computed[:16]}...' if ok else f'⚠ Hash mismatch. Recorded: {recorded[:16]}..., Computed: {computed[:16]}...','success' if ok else 'danger')
    except Exception as e: flash(f'Integrity verification failed: {str(e)}','danger')
    return redirect(url_for('documents.view_document',doc_id=doc_id))

@documents_bp.route('/evidence-pack/<entity_type>/<int:entity_id>')
@login_required
@permission_required('evidence_pack.create')
def generate_evidence_pack(entity_type,entity_id):
    try:
        pack,zip_bytes=DocumentService.generate_evidence_pack(entity_type,entity_id,current_user);response=make_response(zip_bytes);response.headers['Content-Type']='application/zip';response.headers['Content-Disposition']=f'attachment; filename="EvidencePack_{pack.pack_ref}.zip"';return response
    except Exception as e: flash(f'Evidence Pack generation failed: {str(e)}','danger');return redirect(url_for('documents.list_documents'))
