import logging
import os
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException
from app.config import config_by_name
from app.extensions import db, migrate, login_manager, csrf, limiter
from app.models.auth import User

BASE_DIR = Path(__file__).resolve().parent
PACKAGE_TEMPLATE_DIR = BASE_DIR / 'templates'
logger = logging.getLogger(__name__)


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    config_class = config_by_name.get(config_name, config_by_name['default'])
    if config_name == 'production':
        config_class.validate()
    app = Flask(__name__, template_folder=str(PACKAGE_TEMPLATE_DIR))
    app.config.from_object(config_class)
    app.config['APP_ENV'] = config_name
    db.init_app(app)
    migrate.init_app(app, db)
    # Strong session protection invalidates the login session when Flask-Login
    # detects an unexpected client identity change.
    login_manager.session_protection = 'strong'
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from app.services.financial_guard import install_financial_guard
    from app.services.rbac_guard import install_rbac_guard
    install_financial_guard()
    install_rbac_guard(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    @app.after_request
    def security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        response.headers.setdefault(
            'Content-Security-Policy',
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://checkout.razorpay.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
            "connect-src 'self' https://api.razorpay.com; frame-src https://api.razorpay.com https://checkout.razorpay.com; "
            "object-src 'none'; base-uri 'self'; form-action 'self' https://api.razorpay.com; frame-ancestors 'none'"
        )
        if config_name == 'production':
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response

    def _safe_error_response(status, message):
        if request.accept_mimetypes.best == 'application/json' or request.path.startswith('/api/'):
            return jsonify(error=message), status
        return render_template('errors/generic.html', status_code=status, message=message), status

    @app.errorhandler(400)
    def bad_request(error):
        return _safe_error_response(400, 'The request could not be processed.')

    @app.errorhandler(403)
    def forbidden(error):
        return _safe_error_response(403, 'You are not authorised to perform this action.')

    @app.errorhandler(404)
    def not_found(error):
        return _safe_error_response(404, 'The requested resource was not found.')

    @app.errorhandler(429)
    def too_many_requests(error):
        return _safe_error_response(429, 'Too many requests. Please try again later.')

    @app.errorhandler(Exception)
    def unhandled_exception(error):
        if isinstance(error, HTTPException):
            return _safe_error_response(error.code, error.description)
        logger.exception('Unhandled application exception', extra={'path': request.path, 'method': request.method})
        db.session.rollback()
        return _safe_error_response(500, 'An unexpected error occurred. Please try again later.')

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
    from app.routes.privacy import privacy_bp
    for bp in (main_bp, auth_bp, dashboard_bp, donations_bp, income_bp, expenses_bp, vendors_bp,
               budgets_bp, contributions_bp, documents_bp, reports_bp, admin_bp, public_bp,
               controls_bp, reconciliation_bp, account_balances_bp, health_bp, webhooks_bp, privacy_bp):
        app.register_blueprint(bp)

    @app.template_filter('currency')
    def currency_filter(amount):
        return '₹0.00' if amount is None else f'₹{amount:,.2f}'
    return app
