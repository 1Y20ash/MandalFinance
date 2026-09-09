from datetime import datetime
import hmac

from flask import Blueprint, render_template, render_template_string, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import generate_csrf
from flask_limiter.util import get_remote_address
from app.models.auth import User, Role
from app.services.audit_service import AuditService
from app.extensions import db, limiter


auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def login_rate_limit_key():
    """Rate-limit each IP/account combination independently."""
    username = request.form.get('username', '').strip().lower()
    return f"{get_remote_address()}:{username}"


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('5 per minute', methods=['POST'], key_func=login_rate_limit_key)
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        if user and user.check_password(password):
            if user.approval_status != User.APPROVAL_APPROVED or not user.is_active:
                AuditService.log_action(
                    'LOGIN_BLOCKED', 'USER', user.id,
                    'Login blocked because the account is not currently eligible for authentication.',
                )
                flash('Invalid username or password.', 'danger')
                return render_template('auth/login.html')
            login_user(user, remember=remember, fresh=True)
            AuditService.log_action('LOGIN', 'USER', user.id, f"User {user.username} logged in successfully.")
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard.index')
            return redirect(next_page)
        flash('Invalid username or password.', 'danger')
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        if not full_name or not username or not email or not password:
            flash('Please complete all required fields.', 'warning')
            return render_template('auth/register.html')
        if len(password) < 8:
            flash('Password must contain at least 8 characters.', 'warning')
            return render_template('auth/register.html')
        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'warning')
            return render_template('auth/register.html')
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            # Do not reveal whether a particular username/email already exists.
            flash('Registration could not be completed with the supplied account details.', 'warning')
            return render_template('auth/register.html')
        try:
            new_user = User(full_name=full_name, username=username, email=email, phone=phone or None,
                            is_active=False, is_admin=False, approval_status=User.APPROVAL_PENDING,
                            requested_at=datetime.utcnow())
            new_user.set_password(password)
            volunteer_role = Role.query.filter_by(name='Volunteer').first()
            if volunteer_role:
                new_user.roles.append(volunteer_role)
            db.session.add(new_user)
            db.session.flush()
            AuditService.log_action('REGISTER', 'USER', new_user.id,
                f"New user {username} submitted a registration request pending administrator approval.",
                user_override=new_user, commit=False)
            db.session.commit()
            flash('Registration submitted successfully. Your account is pending administrator approval.', 'success')
            return redirect(url_for('auth.login'))
        except Exception:
            db.session.rollback()
            flash('Registration failed. Please try again later.', 'danger')
    return render_template('auth/register.html')


@auth_bp.route('/password/change', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not current_user.check_password(current_password):
        AuditService.log_action('PASSWORD_CHANGE_FAILED', 'USER', current_user.id,
                                'Password change rejected because the current password was invalid.')
        flash('The current password is incorrect.', 'danger')
        return redirect(url_for('auth.profile'))
    if len(new_password) < 8:
        flash('New password must contain at least 8 characters.', 'warning')
        return redirect(url_for('auth.profile'))
    if new_password != confirm_password:
        flash('New passwords do not match.', 'warning')
        return redirect(url_for('auth.profile'))
    if hmac.compare_digest(current_password, new_password):
        flash('New password must be different from the current password.', 'warning')
        return redirect(url_for('auth.profile'))

    user_id = current_user.id
    current_user.set_password(new_password)
    db.session.commit()
    AuditService.log_action('PASSWORD_CHANGED', 'USER', user_id,
                            'User password was changed successfully.', user_override=current_user)
    logout_user()
    flash('Password changed successfully. Please sign in again.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/logout', methods=['GET'])
@login_required
def logout_get():
    """Render a CSRF-protected POST form for the existing navbar logout link."""
    return render_template_string('''<!doctype html><html><head><title>Signing out…</title></head>
<body><form id="logout-form" method="post" action="{{ action }}">
<input type="hidden" name="csrf_token" value="{{ token }}"></form>
<script>document.getElementById('logout-form').submit();</script>
<noscript><p>JavaScript is disabled. Submit the form to sign out.</p><button form="logout-form" type="submit">Sign out</button></noscript></body></html>''', action=url_for('auth.logout'), token=generate_csrf())


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    AuditService.log_action('LOGOUT', 'USER', current_user.id, f"User {current_user.username} logged out.")
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)
