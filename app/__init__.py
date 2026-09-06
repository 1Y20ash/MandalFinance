import os
from flask import Flask
from app.config import config_by_name
from app.extensions import db, migrate, login_manager, csrf
from app.models.auth import User


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    config_class = config_by_name.get(config_name, config_by_name['default'])
    if config_name == 'production':
        config_class.validate()

    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.donations import donations_bp
    from app.routes.income import income_bp
    from app.routes.expenses import expenses_bp
    from app.routes.vendors import vendors_bp
    from app.routes.budgets import budgets_bp
    from app.routes.documents import documents_bp
    from app.routes.reports import reports_bp
    from app.routes.admin import admin_bp
    from app.routes.public import public_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(donations_bp)
    app.register_blueprint(income_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(vendors_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(public_bp)

    @app.template_filter('currency')
    def currency_filter(amount):
        if amount is None:
            return "₹0.00"
        return f"₹{amount:,.2f}"

    return app
