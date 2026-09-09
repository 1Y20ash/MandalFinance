from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models.retention import RetentionPolicy
from app.services.retention_service import RetentionService


def test_retention_policy_calculates_expiry(app):
    with app.app_context():
        policy = RetentionPolicy(
            data_category='TEST_DATA',
            retention_days=30,
            retention_basis='Test policy',
            disposal_action='REVIEW',
        )
        db.session.add(policy)
        db.session.commit()

        created = datetime(2026, 1, 1)
        assert policy.expires_at(created) == datetime(2026, 1, 31)
        assert policy.expires_at(created) > created


def test_due_check_is_deterministic(app):
    with app.app_context():
        policy = RetentionPolicy(
            data_category='TEST_DUE',
            retention_days=30,
            retention_basis='Test policy',
            disposal_action='REVIEW',
        )
        db.session.add(policy)
        db.session.commit()

        created = datetime(2026, 1, 1)
        assert RetentionService.is_due('TEST_DUE', created, datetime(2026, 1, 30)) is False
        assert RetentionService.is_due('TEST_DUE', created, datetime(2026, 1, 31)) is True


def test_missing_policy_is_fail_closed(app):
    with app.app_context():
        with pytest.raises(ValueError, match='No active retention policy'):
            RetentionService.expiry_for('UNDEFINED_DATA', datetime.utcnow())


def test_seed_defaults_does_not_overwrite_existing_policy(app):
    with app.app_context():
        existing = RetentionPolicy(
            data_category='FINANCIAL_RECORDS',
            retention_days=123,
            retention_basis='Approved custom policy',
            disposal_action='REVIEW',
        )
        db.session.add(existing)
        db.session.commit()

        created = RetentionService.seed_defaults()
        assert 'FINANCIAL_RECORDS' not in created
        refreshed = db.session.get(RetentionPolicy, existing.id)
        assert refreshed.retention_days == 123
        assert refreshed.retention_basis == 'Approved custom policy'


def test_retention_policy_rejects_invalid_values(app):
    with app.app_context():
        invalid_days = RetentionPolicy(
            data_category='BAD_DAYS', retention_days=0,
            retention_basis='Invalid', disposal_action='REVIEW'
        )
        db.session.add(invalid_days)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()

        invalid_action = RetentionPolicy(
            data_category='BAD_ACTION', retention_days=30,
            retention_basis='Invalid', disposal_action='PURGE'
        )
        db.session.add(invalid_action)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()
