from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models.auth import User, Role
from app.services.audit_service import AuditService
from app.extensions import db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))

        user = User.query.filter((User.username == username) | (User.email == username)).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact the Mandal Administrator.', 'danger')
                return render_template('auth/login.html')

            login_user(user, remember=remember)
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
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

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
            new_user = User(
                full_name=full_name,
                username=username,
                email=email,
                phone=phone,
                is_active=True,
                is_admin=False
            )
            new_user.set_password(password)

            # Assign default 'Volunteer' role if it exists
            volunteer_role = Role.query.filter_by(name='Volunteer').first()
            if volunteer_role:
                new_user.roles.append(volunteer_role)

            db.session.add(new_user)
            db.session.commit()

            AuditService.log_action('REGISTER', 'USER', new_user.id, f"New user {username} registered successfully.", user_override=new_user)
            flash('Registration successful! You can now log in with your credentials.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Registration failed: {str(e)}', 'danger')

    return render_template('auth/register.html')


@auth_bp.route('/logout')
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
