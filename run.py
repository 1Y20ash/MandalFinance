import os

from app import create_app, db


config_name = os.environ.get("FLASK_ENV", "development")
app = create_app(config_name)


if __name__ == "__main__":
    # Database tables are created automatically only for local development.
    # Production databases must be managed through Flask-Migrate/Alembic.
    if config_name == "development":
        with app.app_context():
            db.create_all()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=app.config.get("DEBUG", False),
    )
