from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app.models.auth import User, Role, Permission
from app.models.audit import AuditLog
from app.models.privacy import PrivacyRequest
from app.extensions import db
from app.utils.decorators import admin_required
from app.services.audit_service import AuditService

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/users')
@login_required
@admin_required
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    roles = Role.query.all()
    pending_users = User.query.filter_by(approval_status=User.APPROVAL_PENDING).order_by(User.requested_at.asc()).all()
    return render_template('admin/users.html', users=users, roles=roles, pending_users=pending_users)


@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    if user.approval_status != User.APPROVAL_PENDING:
        flash(f'User "{user.username}" is not awaiting approval.', 'warning')
        return redirect(url_for('admin.list_users'))
    try:
        user.approval_status = User.APPROVAL_APPROVED
        user.is_active = True
        user.reviewed_at = datetime.utcnow()
        user.approved_by_id = current_user.id
        user.rejection_reason = None
        AuditService.log_action('APPROVE_REGISTRATION', 'USER', user.id,
                                f"Administrator {current_user.username} approved registration for {user.username}.", commit=False)
        db.session.commit()
        flash(f'User "{user.username}" has been approved and can now log in.', 'success')
    except Exception:
        db.session.rollback()
        flash('Unable to approve this registration right now.', 'danger')
    return redirect(url_for('admin.list_users'))


@admin_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    reason = request.form.get('rejection_reason', '').strip()
    if user.approval_status != User.APPROVAL_PENDING:
        flash(f'User "{user.username}" is not awaiting approval.', 'warning')
        return redirect(url_for('admin.list_users'))
    try:
        user.approval_status = User.APPROVAL_REJECTED
        user.is_active = False
        user.reviewed_at = datetime.utcnow()
        user.approved_by_id = current_user.id
        user.rejection_reason = reason or None
        AuditService.log_action('REJECT_REGISTRATION', 'USER', user.id,
                                f"Administrator {current_user.username} rejected registration for {user.username}.", commit=False)
        db.session.commit()
        flash(f'User "{user.username}" registration was rejected.', 'info')
    except Exception:
        db.session.rollback()
        flash('Unable to reject this registration right now.', 'danger')
    return redirect(url_for('admin.list_users'))


@admin_bp.route('/users/<int:user_id>/roles', methods=['POST'])
@login_required
@admin_required
def assign_user_roles(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    role_ids = request.form.getlist('role_ids', type=int)
    selected_roles = Role.query.filter(Role.id.in_(role_ids)).all() if role_ids else []
    old_role_names = sorted(role.name for role in user.roles)
    new_role_names = sorted(role.name for role in selected_roles)
    if old_role_names == new_role_names:
        flash(f'Roles for user "{user.username}" are already up to date.', 'info')
        return redirect(url_for('admin.list_users'))
    try:
        user.roles = selected_roles
        AuditService.log_action('ROLE_CHANGE', 'USER', user.id,
                                f"Administrator {current_user.username} changed roles for {user.username}: {old_role_names or ['<none>']} -> {new_role_names or ['<none>']}.",
                                details={'old_roles': old_role_names, 'new_roles': new_role_names}, commit=False)
        db.session.commit()
        flash(f'Roles updated for user "{user.username}".', 'success')
    except Exception:
        db.session.rollback()
        flash(f'Unable to update roles for user "{user.username}". No changes were saved.', 'danger')
    return redirect(url_for('admin.list_users'))


@admin_bp.route('/roles')
@login_required
@admin_required
def list_roles():
    roles = Role.query.all()
    permissions = Permission.query.order_by(Permission.module.asc()).all()
    return render_template('admin/roles.html', roles=roles, permissions=permissions)


@admin_bp.route('/roles/create', methods=['POST'])
@login_required
@admin_required
def create_role():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    perm_ids = request.form.getlist('permission_ids', type=int)
    if not name:
        flash('Role name is required.', 'danger')
        return redirect(url_for('admin.list_roles'))
    if Role.query.filter_by(name=name).first():
        flash(f'Role "{name}" already exists.', 'warning')
        return redirect(url_for('admin.list_roles'))
    role = Role(name=name, description=description)
    if perm_ids:
        role.permissions = Permission.query.filter(Permission.id.in_(perm_ids)).all()
    db.session.add(role)
    db.session.commit()
    flash(f'Role "{name}" created successfully.', 'success')
    return redirect(url_for('admin.list_roles'))


@admin_bp.route('/roles/<int:role_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_role(role_id):
    role = db.session.get(Role, role_id)
    if role is None:
        abort(404)
    if role.is_system:
        flash(f'System role "{role.name}" cannot be modified.', 'warning')
        return redirect(url_for('admin.list_roles'))
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    perm_ids = request.form.getlist('permission_ids', type=int)
    if not name:
        flash('Role name is required.', 'danger')
        return redirect(url_for('admin.list_roles'))
    duplicate = Role.query.filter(Role.name == name, Role.id != role.id).first()
    if duplicate:
        flash(f'Role "{name}" already exists.', 'warning')
        return redirect(url_for('admin.list_roles'))
    old_name = role.name
    role.name, role.description = name, description
    role.permissions = Permission.query.filter(Permission.id.in_(perm_ids)).all() if perm_ids else []
    AuditService.log_action('UPDATE_ROLE', 'ROLE', role.id,
                            f"Administrator {current_user.username} updated role '{old_name}' to '{role.name}' and changed its permissions.", commit=False)
    db.session.commit()
    flash(f'Role "{role.name}" updated successfully.', 'success')
    return redirect(url_for('admin.list_roles'))


@admin_bp.route('/roles/<int:role_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_role(role_id):
    role = db.session.get(Role, role_id)
    if role is None:
        abort(404)
    if role.is_system:
        flash(f'System role "{role.name}" cannot be deleted.', 'warning')
        return redirect(url_for('admin.list_roles'))
    if role.users:
        flash(f'Role "{role.name}" is assigned to {len(role.users)} user(s). Reassign those users before deleting the role.', 'warning')
        return redirect(url_for('admin.list_roles'))
    role_name = role.name
    AuditService.log_action('DELETE_ROLE', 'ROLE', role.id,
                            f"Administrator {current_user.username} deleted role '{role_name}'.", commit=False)
    db.session.delete(role)
    db.session.commit()
    flash(f'Role "{role_name}" deleted successfully.', 'success')
    return redirect(url_for('admin.list_roles'))


@admin_bp.route('/privacy-requests')
@login_required
@admin_required
def privacy_requests():
    items = PrivacyRequest.query.order_by(PrivacyRequest.requested_at.asc()).all()
    return render_template('admin/privacy_requests.html', items=items)


@admin_bp.route('/privacy-requests/<int:request_id>/status', methods=['POST'])
@login_required
@admin_required
def update_privacy_request(request_id):
    item = db.session.get(PrivacyRequest, request_id)
    if item is None:
        abort(404)
    new_status = (request.form.get('status') or '').upper()
    transitions = {
        'REQUESTED': {'IDENTITY_VERIFIED', 'REJECTED'},
        'IDENTITY_VERIFIED': {'REVIEWED', 'REJECTED'},
        'REVIEWED': {'PROCESSED', 'REJECTED'},
        'PROCESSED': {'COMPLETED'},
        'COMPLETED': set(),
        'REJECTED': set(),
    }
    if new_status not in transitions.get(item.status, set()):
        flash(f'Invalid workflow transition from {item.status} to {new_status}.', 'danger')
        return redirect(url_for('admin.privacy_requests'))

    if new_status == 'PROCESSED' and item.request_type == 'CORRECTION':
        data = item.requested_data or {}
        full_name = str(data.get('full_name') or '').strip()
        email = str(data.get('email') or '').strip().lower()
        phone = str(data.get('phone') or '').strip()
        if not full_name or len(full_name) > 120 or len(phone) > 20 or len(email) > 120 or '@' not in email:
            flash('Correction request contains invalid profile values and cannot be processed.', 'danger')
            return redirect(url_for('admin.privacy_requests'))
        duplicate = User.query.filter(User.email == email, User.id != item.user_id).first()
        if duplicate:
            flash('Correction cannot be processed because the requested email is already in use.', 'danger')
            return redirect(url_for('admin.privacy_requests'))
        target_user = db.session.get(User, item.user_id)
        if target_user is None:
            flash('The request owner could not be found.', 'danger')
            return redirect(url_for('admin.privacy_requests'))
        target_user.full_name = full_name
        target_user.email = email
        target_user.phone = phone or None
        AuditService.log_action('PRIVACY_CORRECTION_PROCESSED', 'user', target_user.id,
                                'Authorized privacy correction request was processed.',
                                {'privacy_request_id': item.id}, commit=False)

    now = datetime.utcnow()
    if new_status == 'IDENTITY_VERIFIED':
        item.verified_at = now
    if new_status == 'COMPLETED':
        item.completed_at = now
    item.status = new_status
    item.reviewed_by_id = current_user.id
    item.response_note = (request.form.get('response_note') or '').strip()[:4000] or None
    AuditService.log_action(
        'PRIVACY_REQUEST_STATUS', 'privacy_request', item.id,
        f'Privacy request status changed to {new_status}.',
        {'status': new_status, 'request_type': item.request_type}, commit=False,
    )
    db.session.commit()
    flash('Privacy request workflow updated.', 'success')
    return redirect(url_for('admin.privacy_requests'))


@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '').strip()
    query = AuditLog.query
    if action_filter:
        query = query.filter_by(action=action_filter)
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/audit_logs.html', pagination=pagination, action_filter=action_filter)
