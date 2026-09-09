from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models.privacy import ConsentRecord, PrivacyRequest
from app.services.audit_service import AuditService
from app.utils.decorators import permission_required

privacy_bp = Blueprint('privacy', __name__, url_prefix='/privacy')

NOTICE_VERSION = '1.0'
CONSENT_PURPOSES = {
    'analytics': 'Optional analytics used to understand aggregate service usage.',
    'communications': 'Optional service communications that are not required to operate the account.',
}
REQUEST_TYPES = {
    'ACCESS': 'Access my personal data',
    'CORRECTION': 'Correct my personal data',
    'DELETION': 'Request deletion of applicable personal data',
    'WITHDRAW_CONSENT': 'Withdraw optional consent',
    'GRIEVANCE': 'Submit a privacy grievance',
}


@privacy_bp.route('/notice')
def notice():
    return render_template('privacy/notice.html', notice_version=NOTICE_VERSION)


@privacy_bp.route('/', methods=['GET', 'POST'])
@login_required
def center():
    if request.method == 'POST':
        request_type = (request.form.get('request_type') or '').upper()
        details = (request.form.get('details') or '').strip()
        if request_type not in REQUEST_TYPES:
            flash('Invalid privacy request type.', 'danger')
            return redirect(url_for('privacy.center'))
        if len(details) > 2000:
            flash('Request details are too long.', 'danger')
            return redirect(url_for('privacy.center'))

        privacy_request = PrivacyRequest(
            user_id=current_user.id,
            request_type=request_type,
            details=details or None,
        )
        db.session.add(privacy_request)
        db.session.flush()
        AuditService.log_action(
            'PRIVACY_REQUEST',
            'privacy_request',
            privacy_request.id,
            f'{request_type} request submitted by authenticated user.',
            {'request_type': request_type},
            commit=False,
        )
        db.session.commit()
        flash('Your privacy request has been recorded. It will be reviewed through the privacy workflow.', 'success')
        return redirect(url_for('privacy.center'))

    consents = ConsentRecord.query.filter_by(user_id=current_user.id).order_by(ConsentRecord.created_at.desc()).all()
    requests = PrivacyRequest.query.filter_by(user_id=current_user.id).order_by(PrivacyRequest.requested_at.desc()).all()
    return render_template(
        'privacy/center.html',
        consents=consents,
        requests=requests,
        consent_purposes=CONSENT_PURPOSES,
        request_types=REQUEST_TYPES,
        notice_version=NOTICE_VERSION,
    )


@privacy_bp.route('/consent', methods=['POST'])
@login_required
def consent():
    purpose = (request.form.get('purpose') or '').strip().lower()
    action = (request.form.get('action') or '').strip().upper()
    if purpose not in CONSENT_PURPOSES or action not in {'GRANT', 'WITHDRAW'}:
        flash('Invalid consent request.', 'danger')
        return redirect(url_for('privacy.center'))

    existing = ConsentRecord.query.filter_by(
        user_id=current_user.id, purpose=purpose, notice_version=NOTICE_VERSION
    ).first()
    now = datetime.utcnow()
    if action == 'GRANT':
        if existing:
            existing.status = 'GRANTED'
            existing.granted_at = now
            existing.withdrawn_at = None
        else:
            existing = ConsentRecord(
                user_id=current_user.id,
                purpose=purpose,
                status='GRANTED',
                notice_version=NOTICE_VERSION,
                source='web',
                granted_at=now,
            )
            db.session.add(existing)
    else:
        if existing:
            existing.status = 'WITHDRAWN'
            existing.withdrawn_at = now
        else:
            existing = ConsentRecord(
                user_id=current_user.id,
                purpose=purpose,
                status='WITHDRAWN',
                notice_version=NOTICE_VERSION,
                source='web',
                granted_at=now,
                withdrawn_at=now,
            )
            db.session.add(existing)

    AuditService.log_action(
        'CONSENT_CHANGE', 'consent', existing.id if existing else None,
        f'Optional {purpose} consent changed to {action}.',
        {'purpose': purpose, 'status': 'GRANTED' if action == 'GRANT' else 'WITHDRAWN', 'notice_version': NOTICE_VERSION},
        commit=False,
    )
    db.session.commit()
    flash('Consent preference updated.', 'success')
    return redirect(url_for('privacy.center'))


@privacy_bp.route('/profile/correction', methods=['POST'])
@login_required
def correction():
    full_name = (request.form.get('full_name') or '').strip()
    phone = (request.form.get('phone') or '').strip()
    email = (request.form.get('email') or '').strip().lower()
    if not full_name or len(full_name) > 120 or len(phone) > 20 or len(email) > 120:
        flash('Please provide valid profile values.', 'danger')
        return redirect(url_for('privacy.center'))
    if '@' not in email:
        flash('Please provide a valid email address.', 'danger')
        return redirect(url_for('privacy.center'))

    current_user.full_name = full_name
    current_user.phone = phone or None
    current_user.email = email
    db.session.commit()
    AuditService.log_action('PRIVACY_CORRECTION', 'user', current_user.id, 'Authenticated user corrected profile data.')
    flash('Your profile data was corrected.', 'success')
    return redirect(url_for('privacy.center'))
