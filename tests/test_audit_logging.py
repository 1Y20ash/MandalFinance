import hashlib
import json

import pytest
from sqlalchemy import text

from app.extensions import db
from app.models.audit import AuditLog
from app.services.audit_service import AuditService


def test_audit_event_is_structured_redacted_and_tamper_evident(app, client):
    with app.test_request_context('/audit-test', headers={'X-Request-ID': 'req-123'}):
        entry = AuditService.log_action(
            'TEST_EVENT',
            'TEST_ENTITY',
            42,
            'A test audit event',
            details={'amount': '100.00', 'password': 'do-not-store', 'nested': {'token': 'secret'}},
        )

    assert entry.event_id
    assert len(entry.integrity_hash) == 64
    assert entry.request_id == 'req-123'
    details = json.loads(entry.details)
    assert details['amount'] == '100.00'
    assert details['password'] == '[REDACTED]'
    assert details['nested']['token'] == '[REDACTED]'
    assert AuditService.verify_integrity()['valid'] is True


def test_audit_update_is_rejected(app):
    with app.app_context():
        entry = AuditService.log_action('UPDATE_TEST', 'TEST', 1, 'immutable test')
        entry.description = 'tampered'
        with pytest.raises(RuntimeError, match='immutable'):
            db.session.commit()
        db.session.rollback()


def test_audit_delete_is_rejected(app):
    with app.app_context():
        entry = AuditService.log_action('DELETE_TEST', 'TEST', 1, 'immutable test')
        db.session.delete(entry)
        with pytest.raises(RuntimeError, match='cannot be deleted'):
            db.session.commit()
        db.session.rollback()


def test_audit_integrity_detects_direct_database_tampering(app):
    with app.app_context():
        entry = AuditService.log_action('TAMPER_TEST', 'TEST', 1, 'integrity test')
        db.session.execute(
            text('UPDATE audit_logs SET description = :description WHERE id = :id'),
            {'description': 'changed outside the ORM', 'id': entry.id},
        )
        db.session.commit()
        result = AuditService.verify_integrity()

    assert result['valid'] is False
    assert entry.id in result['invalid_ids']


def test_audit_is_atomic_when_caller_rolls_back(app):
    with app.app_context():
        before = AuditLog.query.count()
        AuditService.log_action('ATOMIC_TEST', 'TEST', 1, 'must roll back', commit=False)
        assert AuditLog.query.count() == before + 1
        db.session.rollback()
        assert AuditLog.query.count() == before


def test_audit_hash_matches_canonical_record(app):
    with app.app_context():
        entry = AuditService.log_action('HASH_TEST', 'TEST', 1, 'hash test')
        payload = AuditService._canonical_payload(entry).encode('utf-8')
        assert entry.integrity_hash == hashlib.sha256(payload).hexdigest()
