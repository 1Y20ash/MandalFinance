# Database migrations

This directory contains the version-controlled Alembic migration environment for MandalFinance.

Production databases must be migrated with Flask-Migrate/Alembic. Do not use `db.create_all()` in production.

For an existing database that already matches the current SQLAlchemy models, stamp the database at the bootstrap revision before applying later revisions. New schema changes must be introduced as new Alembic revisions.
