import os
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader
from werkzeug.exceptions import HTTPException, TooManyRequests
from app.config import config_by_name
from app.extensions import db, migrate, login_manager, csrf, limiter
from app.models.auth import User
from app.logging_config import configure_logging, install_request_logging
from app.template_fallbacks import TEMPLATE_FALLBACKS
from app.donation_template_fallbacks import DONATION_TEMPLATE_FALLBACKS


BASE_DIR = Path(__file__).resolve().parent
PACKAGE_TEMPLATE_DIR = BASE_DIR / 'templates'


def _template_directory():
    """Use the tracked application template tree as the primary template source."""
    return PACKAGE_TEMPLATE_DIR


def _wants_json_response():
    """Use JSON for explicit API-style clients without leaking exception details."""
    if request.path.startswith('/api/'):
        return True
    return request.accept_mimetypes.best == 'application/json'


def _safe_error_payload(status_code, message):
    return jsonify({
        'error': {
            'code': status_code,
            'message': message,
        }
    }), status_code


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    config_class = config_by_name.get(config_name, config_by_name['default'])
    if config_name == 'production':
        config_class.validate()
    app = Flask(__name__, template_folder=str(_template_directory()))
    app.config.from_object(config_class)
    app.config['APP_ENV'] = config_name

    # Flask keeps the tracked app/templates tree as the source of truth. The
    # DictLoader is a deterministic fallback only for files Vercel's Python
    # bundler omits because Jinja selects them dynamically at runtime.
    app.jinja_loader = ChoiceLoader([
        FileSystemLoader(str(PACKAGE_TEMPLATE_DIR)),
        DictLoader({**TEMPLATE_FALLBACKS, **DONATION_TEMPLATE_FALLBACKS}),
    ])

    configure_logging(app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    install_request_logging(app)
    from app.services.financial_guard import install_financial_guard
    from app.services.rbac_guard import install_rbac_guard
    install_financial_guard()
    install_rbac_guard(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.errorhandler(TooManyRequests)
    def rate_limit_exceeded(error):
        """Return a privacy-safe, user-friendly 429 page without internals."""
        if _wants_json_response():
            return _safe_error_payload(429, 'Too many requests. Please try again later.')
        response = render_template('errors/429.html'), 429
        return response

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        """Normalize expected HTTP failures without exposing framework internals."""
        messages = {
            400: 'The request could not be processed. Please check your input and try again.',
            401: 'Authentication is required to access this resource.',
            403: 'You do not have permission to access this resource.',
            404: 'The requested page could not be found.',
            405: 'This action is not supported for the requested resource.',
            408: 'The request timed out. Please try again.',
            413: 'The submitted content is too large.',
            415: 'The submitted content type is not supported.',
            422: 'The request could not be validated.',
            429: 'Too many requests. Please try again later.',
        }
        status_code = error.code or 500
        message = messages.get(status_code, 'The request could not be completed.')
        if _wants_json_response():
            return _safe_error_payload(status_code, message)
        return render_template('errors/http_error.html', status_code=status_code, message=message), status_code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Log unexpected failures server-side and expose only a generic response."""
        db.session.rollback()
        app.logger.exception('Unhandled application exception')
        if _wants_json_response():
            return _safe_error_payload(500, 'An unexpected error occurred. Please try again later.')
        return render_template('errors/500.html'), 500

    @app.after_request
    def security_headers(response):
        # Phase 22: explicit browser security policy. Keep the policy compatible
        # with the existing server-rendered UI and its trusted CDN dependencies.
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        response.headers.setdefault('Content-Security-Policy',
            "default-src 'self'; "
            "base-uri 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "manifest-src 'self'; "
            "worker-src 'self'; "
            "upgrade-insecure-requests")
        response.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        response.headers.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        if config_name == 'production':
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response

    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.donations import donations_bp
    from app.routes.income import income_bp
    from app.routes.expenses import expenses_bp
    from app.routes.vendors import vendors_bp
    from app.routes.budgets import budgets_bp
    from app.routes.contributions import contributions_bp
    from app.routes.documents import documents_bp
    from app.routes.reports import reports_bp
    from app.routes.admin import admin_bp
    from app.routes.public import public_bp
    from app.routes.financial_controls import controls_bp
    from app.routes.reconciliation import reconciliation_bp
    from app.routes.account_balances import account_balances_bp
    from app.routes.health import health_bp
    from app.routes.webhooks import webhooks_bp
    for bp in (main_bp, auth_bp, dashboard_bp, donations_bp, income_bp, expenses_bp, vendors_bp, budgets_bp, contributions_bp, documents_bp, reports_bp, admin_bp, public_bp, controls_bp, reconciliation_bp, account_balances_bp, health_bp, webhooks_bp):
        app.register_blueprint(bp)

    @app.template_filter('currency')
    def currency_filter(amount):
        return '₹0.00' if amount is None else f'₹{amount:,.2f}'
    return app
