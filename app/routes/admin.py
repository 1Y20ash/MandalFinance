from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app.models.auth import User, Role, Permission
from app.models.audit import AuditLog
from app.extensions import db, limiter
from app.utils.decorators import admin_required
from app.services.audit_service import AuditService


admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/users')
@login_required
@admin_required
@limiter.limit('60 per minute')
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    roles = Role.query.all()
    pending_users = User.query.filter_by(approval_status=User.APPROVAL_PENDING).order_by(User.requested_at.asc()).all()
    return render_template('admin/users.html', users=users, roles=roles, pending_users=pending_users)


@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@login_required
@admin_required
@limiter.limit('30 per minute', methods=['POST'])
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

        AuditService.log_action(
            'APPROVE_REGISTRATION',
            'USER',
            user.id,
            f"Administrator {current_user.username} approved registration for {user.username}.",
            commit=False,
        )
        db.session.commit()
        flash(f'User "{user.username}" has been approved and can now log in.', 'success')
    except Exception:
        db.session.rollback()
        flash('Unable to approve this registration right now.', 'danger')

    return redirect(url_for('admin.list_users'))


@admin_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@login_required
@admin_required
@limiter.limit('30 per minute', methods=['POST'])
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

        AuditService.log_action(
            'REJECT_REGISTRATION',
            'USER',
            user.id,
            f"Administrator {current_user.username} rejected registration for {user.username}.",
            commit=False,
        )
        db.session.commit()
        flash(f'User "{user.username}" registration was rejected.', 'info')
    except Exception:
        db.session.rollback()
        flash('Unable to reject this registration right now.', 'danger')

    return redirect(url_for('admin.list_users'))


@admin_bp.route('/users/<int:user_id>/roles', methods=['POST'])
@login_required
@admin_required
@limiter.limit('30 per minute', methods=['POST'])
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
        AuditService.log_action(
            'ROLE_CHANGE',
            'USER',
            user.id,
            f"Administrator {current_user.username} changed roles for {user.username}: "
            f"{old_role_names or ['<none>']} -> {new_role_names or ['<none>']}.",
            details={'old_roles': old_role_names, 'new_roles': new_role_names},
            commit=False,
        )
        db.session.commit()
        flash(f'Roles updated for user "{user.username}".', 'success')
    except Exception:
        db.session.rollback()
        flash(f'Unable to update roles for user "{user.username}". No changes were saved.', 'danger')

    return redirect(url_for('admin.list_users'))


@admin_bp.route('/roles')
@login_required
@admin_required
@limiter.limit('60 per minute')
def list_roles():
    roles = Role.query.all()
    permissions = Permission.query.order_by(Permission.module.asc()).all()
    return render_template('admin/roles.html', roles=roles, permissions=permissions)


@admin_bp.route('/roles/create', methods=['POST'])
@login_required
@admin_required
@limiter.limit('30 per minute', methods=['POST'])
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
@limiter.limit('30 per minute', methods=['POST'])
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
    role.name = name
    role.description = description
    role.permissions = Permission.query.filter(Permission.id.in_(perm_ids)).all() if perm_ids else []

    AuditService.log_action(
        'UPDATE_ROLE',
        'ROLE',
        role.id,
        f"Administrator {current_user.username} updated role '{old_name}' to '{role.name}' and changed its permissions.",
        commit=False,
    )
    db.session.commit()
    flash(f'Role "{role.name}" updated successfully.', 'success')
    return redirect(url_for('admin.list_roles'))


@admin_bp.route('/roles/<int:role_id>/delete', methods=['POST'])
@login_required
@admin_required
@limiter.limit('30 per minute', methods=['POST'])
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
    role_id_value = role.id
    AuditService.log_action(
        'DELETE_ROLE',
        'ROLE',
        role_id_value,
        f"Administrator {current_user.username} deleted role '{role_name}'.",
        commit=False,
    )
    db.session.delete(role)
    db.session.commit()
    flash(f'Role "{role_name}" deleted successfully.', 'success')
    return redirect(url_for('admin.list_roles'))


@admin_bp.route('/audit-logs')
@login_required
@admin_required
@limiter.limit('60 per minute')
def audit_logs():
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '').strip()

    query = AuditLog.query
    if action_filter:
        query = query.filter_by(action=action_filter)

    pagination = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/audit_logs.html', pagination=pagination, action_filter=action_filter)
