from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user

from app.models.deletion import DeletionRequest
from app.services.deletion_service import DeletionService
from app.utils.decorators import admin_required


privacy_bp = Blueprint('privacy', __name__, url_prefix='/privacy')


@privacy_bp.route('/deletion', methods=['GET', 'POST'])
@login_required
def deletion_request():
    if request.method == 'POST':
        reason = request.form.get('reason', '').strip()
        try:
            DeletionService.request_for_user(current_user, reason=reason)
            flash('Your deletion request has been submitted for controlled review.', 'success')
        except ValueError as exc:
            flash(str(exc), 'warning')
        return redirect(url_for('privacy.deletion_request'))

    requests = DeletionRequest.query.filter_by(
        requested_by_id=current_user.id
    ).order_by(DeletionRequest.requested_at.desc()).all()
    return render_template('privacy/deletion.html', requests=requests)


@privacy_bp.route('/deletion/<int:request_id>/cancel', methods=['POST'])
@login_required
def cancel_deletion_request(request_id):
    deletion = DeletionRequest.query.filter_by(
        id=request_id, requested_by_id=current_user.id, status='PENDING'
    ).first()
    if deletion is None:
        flash('Only your pending deletion requests can be cancelled.', 'warning')
        return redirect(url_for('privacy.deletion_request'))

    deletion.status = 'REJECTED'
    deletion.decision_reason = 'Cancelled by the requesting user.'
    from app.extensions import db
    from app.services.audit_service import AuditService
    AuditService.log_action(
        'CANCEL_DELETION', 'DELETION_REQUEST', deletion.id,
        'User cancelled their pending privacy deletion request.',
        user_override=current_user, commit=False,
    )
    db.session.commit()
    flash('Deletion request cancelled.', 'info')
    return redirect(url_for('privacy.deletion_request'))


@privacy_bp.route('/deletion/<int:request_id>/complete')
@login_required
@admin_required
def admin_complete_deletion(request_id):
    deletion = DeletionRequest.query.filter_by(id=request_id).first()
    if deletion is None:
        return ('Deletion request not found.', 404)
    try:
        DeletionService.review(
            request_id,
            current_user,
            approve=True,
            decision_reason='Approved by administrator.',
        )
        flash('Deletion request processed.', 'success')
    except ValueError as exc:
        flash(str(exc), 'warning')
    return redirect(url_for('admin.deletion_requests'))
