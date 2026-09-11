from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app.models.auth import User, Role, Permission
from app.models.audit import AuditLog
from app.models.mandal import Mandal, FinancialYear, Event
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


@admin_bp.route('/financial-events')
@login_required
@admin_required
@limiter.limit('60 per minute')
def financial_events():
    events = Event.query.order_by(Event.year.desc(), Event.start_date.desc(), Event.id.desc()).all()
    financial_years = FinancialYear.query.order_by(FinancialYear.start_date.desc(), FinancialYear.id.desc()).all()
    mandals = Mandal.query.order_by(Mandal.name.asc()).all()
    active_event = Event.query.filter_by(is_active=True).order_by(Event.id.asc()).first()
    return render_template(
        'admin/financial_events.html',
        events=events,
        financial_years=financial_years,
        mandals=mandals,
        active_event=active_event,
    )


@admin_bp.route('/financial-years/create', methods=['POST'])
@login_required
@admin_required
@limiter.limit('20 per minute', methods=['POST'])
def create_financial_year():
    name = request.form.get('name', '').strip()
    start_raw = request.form.get('start_date', '').strip()
    end_raw = request.form.get('end_date', '').strip()
    opening_raw = request.form.get('opening_balance', '0').strip()
    notes = request.form.get('notes', '').strip() or None

    try:
        start_date = datetime.strptime(start_raw, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_raw, '%Y-%m-%d').date()
        opening_balance = Decimal(opening_raw).quantize(Decimal('0.01'))
        if not name:
            raise ValueError('Financial year name is required.')
        if start_date > end_date:
            raise ValueError('Financial year start date cannot be after the end date.')
        if opening_balance < 0:
            raise ValueError('Opening balance cannot be negative.')
        if FinancialYear.query.filter_by(name=name).first():
            raise ValueError(f'Financial year "{name}" already exists.')

        fy = FinancialYear(
            name=name,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
            is_locked=False,
            opening_balance=opening_balance,
            notes=notes,
        )
        db.session.add(fy)
        db.session.flush()
        AuditService.log_action(
            'CREATE', 'FINANCIAL_YEAR', fy.id,
            f'Administrator {current_user.username} created financial year {fy.name}.',
            commit=False,
        )
        db.session.commit()
        flash(f'Financial year "{fy.name}" created.', 'success')
    except (ValueError, InvalidOperation, TypeError) as exc:
        db.session.rollback()
        flash(str(exc), 'danger')

    return redirect(url_for('admin.financial_events'))


@admin_bp.route('/financial-events/create', methods=['POST'])
@login_required
@admin_required
@limiter.limit('20 per minute', methods=['POST'])
def create_financial_event():
    title = request.form.get('title', '').strip()
    year = request.form.get('year', type=int)
    mandal_id = request.form.get('mandal_id', type=int)
    financial_year_id = request.form.get('financial_year_id', type=int)
    start_raw = request.form.get('start_date', '').strip()
    end_raw = request.form.get('end_date', '').strip()
    budget_raw = request.form.get('budget_target', '0').strip()

    try:
        if not title:
            raise ValueError('Event title is required.')
        if not year or year < 2000 or year > 2100:
            raise ValueError('Event year must be between 2000 and 2100.')
        mandal = db.session.get(Mandal, mandal_id) if mandal_id else None
        fy = db.session.get(FinancialYear, financial_year_id) if financial_year_id else None
        if not mandal:
            raise ValueError('Select a valid mandal.')
        if not fy:
            raise ValueError('Select a valid financial year.')
        if fy.is_locked:
            raise ValueError('A locked financial year cannot receive a new event.')
        start_date = datetime.strptime(start_raw, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_raw, '%Y-%m-%d').date()
        if start_date > end_date:
            raise ValueError('Event start date cannot be after the end date.')
        if start_date < fy.start_date or end_date > fy.end_date:
            raise ValueError('Event dates must fall within the selected financial year.')
        budget_target = Decimal(budget_raw).quantize(Decimal('0.01'))
        if budget_target < 0:
            raise ValueError('Budget target cannot be negative.')

        event = Event(
            mandal_id=mandal.id,
            financial_year_id=fy.id,
            title=title,
            year=year,
            start_date=start_date,
            end_date=end_date,
            is_active=False,
            status='OPEN',
            budget_target=budget_target,
        )
        db.session.add(event)
        db.session.flush()
        AuditService.log_action(
            'CREATE', 'EVENT', event.id,
            f'Administrator {current_user.username} created event {event.title} in OPEN/inactive state.',
            commit=False,
        )
        db.session.commit()
        flash(f'Event "{event.title}" created. Activate it when it is operationally ready.', 'success')
    except (ValueError, InvalidOperation, TypeError) as exc:
        db.session.rollback()
        flash(str(exc), 'danger')

    return redirect(url_for('admin.financial_events'))


@admin_bp.route('/financial-events/<int:event_id>/activate', methods=['POST'])
@login_required
@admin_required
@limiter.limit('20 per minute', methods=['POST'])
def activate_financial_event(event_id):
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    if event.status != 'OPEN':
        flash('Only an OPEN event can be activated. Closed or locked events must not be reopened through this control.', 'warning')
        return redirect(url_for('admin.financial_events'))
    if event.financial_year is None or event.financial_year.is_locked:
        flash('This event cannot be activated because its financial year is locked or unavailable.', 'danger')
        return redirect(url_for('admin.financial_events'))
    if event.start_date > event.end_date:
        flash('This event has invalid dates and cannot be activated.', 'danger')
        return redirect(url_for('admin.financial_events'))

    try:
        previous_active = Event.query.filter(Event.is_active.is_(True), Event.id != event.id).all()
        for other in previous_active:
            other.is_active = False
            AuditService.log_action(
                'DEACTIVATE', 'EVENT', other.id,
                f'Event {other.title} was deactivated because administrator {current_user.username} activated event {event.title}.',
                commit=False,
            )

        event.is_active = True
        AuditService.log_action(
            'ACTIVATE', 'EVENT', event.id,
            f'Administrator {current_user.username} activated event {event.title}.',
            commit=False,
        )
        db.session.commit()
        flash(f'Financial event "{event.title}" is now ACTIVE and OPEN. The public donation portal can use it.', 'success')
    except Exception:
        db.session.rollback()
        flash('Unable to activate the financial event. No changes were saved.', 'danger')

    return redirect(url_for('admin.financial_events'))


@admin_bp.route('/financial-events/<int:event_id>/deactivate', methods=['POST'])
@login_required
@admin_required
@limiter.limit('20 per minute', methods=['POST'])
def deactivate_financial_event(event_id):
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)
    if event.status != 'OPEN':
        flash('Only an OPEN event can be deactivated.', 'warning')
        return redirect(url_for('admin.financial_events'))

    try:
        event.is_active = False
        AuditService.log_action(
            'DEACTIVATE', 'EVENT', event.id,
            f'Administrator {current_user.username} deactivated event {event.title}.',
            commit=False,
        )
        db.session.commit()
        flash(f'Financial event "{event.title}" is now inactive. No public donation event is selected.', 'success')
    except Exception:
        db.session.rollback()
        flash('Unable to deactivate the financial event. No changes were saved.', 'danger')

    return redirect(url_for('admin.financial_events'))


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
