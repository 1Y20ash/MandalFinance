from functools import wraps
from flask import flash, redirect, url_for, request, abort
from flask_login import current_user

def permission_required(perm_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            if not current_user.has_permission(perm_name):
                flash(f'Access denied: You do not have permission "{perm_name}".', 'danger')
                abort(403)
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Administrator access required.', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
