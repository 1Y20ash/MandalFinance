import base64
import hashlib
import hmac
import os
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash
from app.extensions import db


PASSWORD_HASH_ALGORITHM = 'sha256'
PASSWORD_ITERATIONS = 600_000
PASSWORD_SALT_BYTES = 32

role_permissions = db.Table(
    'role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True)
)

user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)
)


class Permission(db.Model):
    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    module = db.Column(db.String(50), nullable=False, default='general')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Permission {self.name}>'


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    is_system = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    permissions = db.relationship('Permission', secondary=role_permissions, lazy='subquery',
                                  backref=db.backref('roles', lazy=True))

    def has_permission(self, perm_name):
        return any(p.name == perm_name for p in self.permissions)

    def __repr__(self):
        return f'<Role {self.name}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    APPROVAL_PENDING = 'PENDING'
    APPROVAL_APPROVED = 'APPROVED'
    APPROVAL_REJECTED = 'REJECTED'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    approval_status = db.Column(db.String(20), nullable=False, default=APPROVAL_APPROVED, index=True)
    requested_at = db.Column(db.DateTime, nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    rejection_reason = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
                            backref=db.backref('users', lazy=True))
    approved_by = db.relationship('User', remote_side=[id], foreign_keys=[approved_by_id],
                                  backref=db.backref('approved_users', lazy=True))

    @property
    def is_authenticated(self):
        """Keep an already-authenticated session addressable after account revocation.

        Flask-Login's ``UserMixin`` derives this property from ``is_active``. That
        would turn a mid-session deactivation into an anonymous session and cause
        ``login_required`` to redirect to login, bypassing the application's
        authorization boundary. Login eligibility is still enforced by
        ``login_user`` and the login route; existing sessions are denied with 403
        by the authorization decorators when ``is_active`` or approval changes.
        """
        return True

    @property
    def is_anonymous(self):
        return False

    def set_password(self, password):
        """Hash a password with a unique cryptographically random 32-byte salt."""
        if not isinstance(password, str) or len(password) < 8:
            raise ValueError('Password must be a string with at least 8 characters.')

        salt = os.urandom(PASSWORD_SALT_BYTES)
        derived_key = hashlib.pbkdf2_hmac(
            PASSWORD_HASH_ALGORITHM,
            password.encode('utf-8'),
            salt,
            PASSWORD_ITERATIONS,
        )
        salt_text = base64.urlsafe_b64encode(salt).decode('ascii').rstrip('=')
        key_text = base64.urlsafe_b64encode(derived_key).decode('ascii').rstrip('=')
        self.password_hash = f'pbkdf2_sha256${PASSWORD_ITERATIONS}${salt_text}${key_text}'

    def check_password(self, password):
        """Verify the explicit PBKDF2 format while retaining legacy hash compatibility."""
        if not isinstance(password, str):
            return False

        if self.password_hash.startswith('pbkdf2_sha256$'):
            try:
                _, iterations_text, salt_text, stored_key_text = self.password_hash.split('$', 3)
                iterations = int(iterations_text)
                padding = '=' * (-len(salt_text) % 4)
                salt = base64.urlsafe_b64decode(salt_text + padding)
                padding = '=' * (-len(stored_key_text) % 4)
                stored_key = base64.urlsafe_b64decode(stored_key_text + padding)
                derived_key = hashlib.pbkdf2_hmac(
                    PASSWORD_HASH_ALGORITHM,
                    password.encode('utf-8'),
                    salt,
                    iterations,
                )
                return hmac.compare_digest(derived_key, stored_key)
            except (ValueError, TypeError):
                return False

        # Existing accounts may still contain the previous Werkzeug format.
        return check_password_hash(self.password_hash, password)

    def has_permission(self, perm_name):
        """Check authorization from current DB rows rather than cached relationships."""
        if self.is_admin:
            return True
        permission_id = (
            db.session.query(Permission.id)
            .join(role_permissions, role_permissions.c.permission_id == Permission.id)
            .join(Role, Role.id == role_permissions.c.role_id)
            .join(user_roles, user_roles.c.role_id == Role.id)
            .filter(
                user_roles.c.user_id == self.id,
                Permission.name == perm_name,
            )
            .first()
        )
        return permission_id is not None

    def get_permissions(self):
        perms = set()
        for role in self.roles:
            for p in role.permissions:
                perms.add(p.name)
        return list(perms)

    def __repr__(self):
        return f'<User {self.username}>'
