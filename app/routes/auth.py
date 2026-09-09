from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf.csrf import generate_csrf
from flask_limiter.util import get_remote_address
from app.models.auth import User, Role
from app.services.audit_service import AuditService
from app.extensions import db, limiter
from app.utils.security import is_safe_local_redirect


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
            if user.approval_status == User.APPROVAL_PENDING:
                AuditService.log_action('LOGIN_BLOCKED', 'USER', user.id, 'Login blocked because account approval is pending.', outcome='failure')
                flash('Your registration is pending administrator approval. Please try again after your account is approved.', 'warning')
                return render_template('auth/login.html')
            if user.approval_status == User.APPROVAL_REJECTED:
                AuditService.log_action('LOGIN_BLOCKED', 'USER', user.id, 'Login blocked because registration was rejected.', outcome='failure')
                flash('Your registration request was rejected. Please contact the Mandal Administrator for further details.', 'danger')
                return render_template('auth/login.html')
            if not user.is_active:
                AuditService.log_action('LOGIN_BLOCKED', 'USER', user.id, 'Login blocked because the account is inactive.', outcome='failure')
                flash('Your account has been deactivated. Please contact the Mandal Administrator.', 'danger')
                return render_template('auth/login.html')
            login_user(user, remember=remember)
            AuditService.log_action('LOGIN', 'USER', user.id, f"User {user.username} logged in successfully.")
            next_page = request.args.get('next')
            if not is_safe_local_redirect(next_page):
                next_page = url_for('dashboard.index')
            return redirect(next_page)
        AuditService.log_action('LOGIN_FAILED', 'AUTH', None, 'A login attempt failed due to invalid credentials.', outcome='failure')
        flash('Invalid username or password.', 'danger')
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit('5 per hour', methods=['POST'])
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
        if User.query.filter_by(username=username).first():
            flash('Username is already taken. Please choose a different username.', 'warning')
            return render_template('auth/register.html')
        if User.query.filter_by(email=email).first():
            flash('An account with this email address already exists.', 'warning')
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


@auth_bp.route('/logout', methods=['GET'])
@login_required
def logout_get():
    """Render a CSRF-protected POST form for the existing navbar logout link."""
    return render_template('auth/logout.html', action=url_for('auth.logout'), token=generate_csrf())


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
