import os
from flask import Flask
from app.config import config_by_name
from app.extensions import db,migrate,login_manager,csrf,limiter
from app.models.auth import User


def create_app(config_name=None):
    if config_name is None: config_name=os.environ.get('FLASK_ENV','development')
    config_class=config_by_name.get(config_name,config_by_name['default'])
    if config_name=='production': config_class.validate()
    app=Flask(__name__);app.config.from_object(config_class);app.config['APP_ENV']=config_name
    db.init_app(app);migrate.init_app(app,db);login_manager.init_app(app);csrf.init_app(app);limiter.init_app(app)
    from app.services.financial_guard import install_financial_guard
    from app.services.rbac_guard import install_rbac_guard
    install_financial_guard()
    install_rbac_guard(app)

    @login_manager.user_loader
    def load_user(user_id): return db.session.get(User,int(user_id))

    @app.after_request
    def security_headers(response):
        response.headers.setdefault('X-Content-Type-Options','nosniff');response.headers.setdefault('X-Frame-Options','DENY');response.headers.setdefault('Referrer-Policy','strict-origin-when-cross-origin');response.headers.setdefault('Permissions-Policy','camera=(), microphone=(), geolocation=()')
        if config_name=='production': response.headers.setdefault('Strict-Transport-Security','max-age=31536000; includeSubDomains')
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
    for bp in (main_bp,auth_bp,dashboard_bp,donations_bp,income_bp,expenses_bp,vendors_bp,budgets_bp,contributions_bp,documents_bp,reports_bp,admin_bp,public_bp,controls_bp,reconciliation_bp,account_balances_bp,health_bp): app.register_blueprint(bp)

    @app.template_filter('currency')
    def currency_filter(amount): return '₹0.00' if amount is None else f'₹{amount:,.2f}'
    return app
