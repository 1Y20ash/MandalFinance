import os
from pathlib import Path
from flask import Flask, render_template_string
from werkzeug.exceptions import HTTPException
from app.config import config_by_name
from app.extensions import db, migrate, login_manager, csrf, limiter
from app.models.auth import User

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
PACKAGE_TEMPLATE_DIR = BASE_DIR / 'templates'
DEPLOYED_TEMPLATE_DIR = PROJECT_DIR / 'templates'
TEMPLATE_DIR = DEPLOYED_TEMPLATE_DIR if DEPLOYED_TEMPLATE_DIR.exists() else PACKAGE_TEMPLATE_DIR


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    config_class = config_by_name.get(config_name, config_by_name['default'])
    if config_name == 'production':
        config_class.validate()
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR))
    app.config.from_object(config_class)
    app.config['APP_ENV'] = config_name
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from app.services.financial_guard import install_financial_guard
    from app.services.rbac_guard import install_rbac_guard
    from app.services.retention_service import RetentionService
    install_financial_guard()
    install_rbac_guard(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.cli.command('purge-audit-logs')
    def purge_audit_logs():
        """Apply the configured audit-log retention policy."""
        result = RetentionService.purge_audit_logs(
            financial_days=app.config['AUDIT_FINANCIAL_RETENTION_DAYS'],
            security_days=app.config['AUDIT_SECURITY_RETENTION_DAYS'],
        )
        print(f"Purged {result['total_deleted']} audit records ({result['financial_deleted']} financial, {result['security_deleted']} security).")

    @app.after_request
    def security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        if config_name == 'production':
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        if error.code == 429:
            return render_template_string('<!doctype html><title>Too many requests</title><h1>Too many requests</h1><p>Please wait a moment and try again.</p>'), 429
        message = error.description if error.code not in (401, 403) else 'You are not authorized to perform this action.'
        return render_template_string('<!doctype html><title>{{ title }}</title><h1>{{ title }}</h1><p>{{ message }}</p>', title=error.name, message=message), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        if isinstance(error, HTTPException):
            return error
        app.logger.exception('Unhandled application exception')
        return render_template_string('<!doctype html><title>Something went wrong</title><h1>Something went wrong</h1><p>Please try again later.</p>'), 500

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
