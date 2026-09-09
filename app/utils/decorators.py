from functools import wraps

from flask import abort, flash, redirect, request, url_for
from flask_login import current_user

from app.services.audit_service import AuditService


def _deny_authorization(action, permission=None):
    """Record a minimal authorization denial without exposing policy internals."""
    target = request.path[:255]
    details = {'path': target, 'method': request.method}
    if permission:
        details['permission'] = permission
    try:
        AuditService.log_action(
            action,
            'AUTHORIZATION',
            getattr(current_user, 'id', None),
            'Authorization denied for the requested resource.',
            details=details,
        )
    except Exception:
        # Authorization must remain fail-closed even if audit persistence is unavailable.
        pass


def permission_required(perm_name):
    """Require authentication plus the named server-side permission."""
    if not isinstance(perm_name, str) or not perm_name.strip():
        raise ValueError('A non-empty permission name is required.')
    required_permission = perm_name.strip()

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))

            # Authentication eligibility is checked again at the authorization boundary
            # so a deactivated/unapproved session cannot retain application privileges.
            if not current_user.is_active or getattr(current_user, 'approval_status', None) != 'APPROVED':
                _deny_authorization('AUTHORIZATION_DENIED_INELIGIBLE_USER')
                abort(403)

            if not current_user.has_permission(required_permission):
                _deny_authorization('AUTHORIZATION_DENIED', required_permission)
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(f):
    """Require an active, approved administrator for administrative routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_active or getattr(current_user, 'approval_status', None) != 'APPROVED':
            _deny_authorization('ADMIN_AUTHORIZATION_DENIED_INELIGIBLE_USER')
            abort(403)
        if not current_user.is_admin:
            _deny_authorization('ADMIN_AUTHORIZATION_DENIED')
            abort(403)
        return f(*args, **kwargs)

    return decorated_function
