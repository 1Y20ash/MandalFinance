from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app.models.auth import User, Role, Permission
from app.models.audit import AuditLog
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
def assign_user_roles(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    role_ids = request.form.getlist('role_ids', type=int)

    selected_roles = Role.query.filter(Role.id.in_(role_ids)).all() if role_ids else []
    user.roles = selected_roles
    db.session.commit()

    flash(f'Roles updated for user "{user.username}".', 'success')
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
