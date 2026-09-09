from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from app.extensions import db
from app.models.auth import User
from app.models.privacy import ConsentRecord, PrivacyRequest
from app.services.audit_service import AuditService

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
        if request_type not in REQUEST_TYPES or len(details) > 2000:
            flash('Invalid privacy request.', 'danger')
            return redirect(url_for('privacy.center'))
        item = PrivacyRequest(user_id=current_user.id, request_type=request_type, details=details or None)
        db.session.add(item)
        db.session.flush()
        AuditService.log_action('PRIVACY_REQUEST', 'privacy_request', item.id,
                                f'{request_type} request submitted by authenticated user.',
                                {'request_type': request_type}, commit=False)
        db.session.commit()
        flash('Your privacy request has been recorded and is awaiting review.', 'success')
        return redirect(url_for('privacy.center'))
    consents = ConsentRecord.query.filter_by(user_id=current_user.id).order_by(ConsentRecord.created_at.desc()).all()
    requests = PrivacyRequest.query.filter_by(user_id=current_user.id).order_by(PrivacyRequest.requested_at.desc()).all()
    return render_template('privacy/center.html', consents=consents, requests=requests,
                           consent_purposes=CONSENT_PURPOSES, request_types=REQUEST_TYPES,
                           notice_version=NOTICE_VERSION)


@privacy_bp.route('/consent', methods=['POST'])
@login_required
def consent():
    purpose = (request.form.get('purpose') or '').strip().lower()
    action = (request.form.get('action') or '').strip().upper()
    if purpose not in CONSENT_PURPOSES or action not in {'GRANT', 'WITHDRAW'}:
        flash('Invalid consent request.', 'danger')
        return redirect(url_for('privacy.center'))

    # Granting optional processing requires an explicit affirmative control.
    # Withdrawal remains a one-step action and is never made harder than grant.
    if action == 'GRANT' and request.form.get('consent_confirm') != 'yes':
        flash('Please explicitly confirm this optional consent before granting it.', 'warning')
        return redirect(url_for('privacy.center'))

    existing = ConsentRecord.query.filter_by(
        user_id=current_user.id, purpose=purpose, notice_version=NOTICE_VERSION
    ).first()
    now = datetime.utcnow()
    previous_status = existing.status if existing else 'NOT_GRANTED'

    if action == 'GRANT':
        if existing:
            existing.status, existing.granted_at, existing.withdrawn_at = 'GRANTED', now, None
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
            existing.status, existing.withdrawn_at = 'WITHDRAWN', now
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
        'CONSENT_CHANGE', 'consent', existing.id,
        f'Optional {purpose} consent changed from {previous_status} to {existing.status}.',
        {
            'purpose': purpose,
            'previous_status': previous_status,
            'status': existing.status,
            'notice_version': NOTICE_VERSION,
            'source': 'web',
        },
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
    if not full_name or len(full_name) > 120 or len(phone) > 20 or len(email) > 120 or '@' not in email:
        flash('Please provide valid profile values.', 'danger')
        return redirect(url_for('privacy.center'))
    if User.query.filter(User.email == email, User.id != current_user.id).first():
        flash('That email address is already in use.', 'danger')
        return redirect(url_for('privacy.center'))
    current_user.full_name, current_user.phone, current_user.email = full_name, phone or None, email
    db.session.commit()
    AuditService.log_action('PRIVACY_CORRECTION', 'user', current_user.id, 'Authenticated user corrected profile data.')
    flash('Your profile data was corrected.', 'success')
    return redirect(url_for('privacy.center'))
