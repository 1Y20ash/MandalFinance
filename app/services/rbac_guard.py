from flask import request, jsonify
from flask_login import current_user


# Financial-control endpoints are deliberately protected here as a second server-side
# authorization layer. Individual write handlers keep their existing business checks.
VIEW_PATHS = (
    '/finance-controls/events',
    '/finance-controls/sponsorships',
    '/finance-controls/members',
    '/finance-controls/reconciliations',
    '/finance-controls/evidence/',
    '/finance-controls/timeline/',
    '/finance-controls/reports/',
    '/finance-controls/notifications',
)


def install_rbac_guard(app):
    if getattr(app, '_mandal_rbac_guard_installed', False):
        return

    @app.before_request
    def _finance_route_guard():
        path = request.path
        if not path.startswith('/finance-controls') or not current_user.is_authenticated:
            return None
        if current_user.is_admin:
            return None

        if request.method == 'GET':
            if current_user.has_permission('finance.view'):
                return None
            return jsonify({'error': 'Financial view permission required.'}), 403

        # Mutating finance-control operations require the dedicated finance.manage
        # permission. This prevents a broad expense/donation create permission from
        # becoming an accidental gateway into reconciliation/correction controls.
        if current_user.has_permission('finance.manage'):
            return None
        return jsonify({'error': 'Financial management permission required.'}), 403

    app._mandal_rbac_guard_installed = True
