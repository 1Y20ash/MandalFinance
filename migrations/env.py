import os
from logging.config import fileConfig

from alembic import context
from flask import current_app

# Alembic Config object, which provides access to values in alembic.ini.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so SQLAlchemy metadata is complete for autogenerate.
from app import create_app, db  # noqa: E402
import app.models  # noqa: F401,E402

config.set_main_option(
    "sqlalchemy.url",
    current_app.config.get("SQLALCHEMY_DATABASE_URI", ""),
)

target_metadata = db.metadata


def get_url():
    return current_app.config.get("SQLALCHEMY_DATABASE_URI", "")


def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = current_app.extensions["migrate"].db.engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
