import os

from flask_migrate import upgrade

from app import create_app


config_name = os.environ.get("FLASK_ENV", "development")
app = create_app(config_name)


if __name__ == "__main__":
    # Keep database schema management in Flask-Migrate/Alembic instead of
    # creating tables directly from SQLAlchemy metadata.
    if config_name == "development":
        with app.app_context():
            upgrade()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=app.config.get("DEBUG", False),
    )
