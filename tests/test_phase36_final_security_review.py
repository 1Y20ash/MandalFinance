from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def test_final_security_review_exists_and_is_not_a_legal_certification():
    text = read('docs/FINAL_SECURITY_REVIEW.md')
    assert 'Phase 36' in text
    assert 'not a legal' in text.lower()
    assert 'not a' in text.lower()
    assert 'Phase 37' in text


def test_review_covers_release_critical_security_domains():
    text = read('docs/FINAL_SECURITY_REVIEW.md').lower()
    required = [
        'configuration and secrets',
        'authentication',
        'authorization',
        'csrf',
        'financial integrity',
        'payment security',
        'webhooks',
        'document security',
        'database',
        'logging / audit',
        'security headers',
        'rate limiting',
        'error handling',
        'frontend privacy',
        'third-party processors',
        'health checks',
        'dpdp governance',
    ]
    for item in required:
        assert item in text


def test_review_preserves_known_csp_hardening_note():
    text = read('docs/FINAL_SECURITY_REVIEW.md')
    assert "'unsafe-inline'" in text
    assert 'nonce/hash' in text


def test_review_does_not_convert_environment_specific_work_into_false_passes():
    text = read('docs/FINAL_SECURITY_REVIEW.md').lower()
    for phrase in (
        'real production payment',
        'live private-object authorization',
        'actual production redis',
        'live deployment topology',
        'final production smoke',
    ):
        assert phrase in text
    assert 'must not be bypassed' in text


def test_production_configuration_has_fail_closed_security_boundaries():
    text = read('app/config.py')
    assert "postgresql://" in text
    assert "Mock payment gateway is forbidden in production." in text
    assert "SUPABASE_STORAGE_PRIVATE must be true in production." in text
    assert "memory://" in text
    assert "RAZORPAY_WEBHOOK_SECRET" in text
    assert "REDIS_PROVIDER_NAME" in text


def test_application_security_headers_and_global_error_boundary_remain_present():
    text = read('app/__init__.py')
    for marker in (
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Content-Security-Policy",
        "Strict-Transport-Security",
        "@app.errorhandler(Exception)",
        "db.session.rollback()",
        "app.logger.exception('Unhandled application exception')",
    ):
        assert marker in text


def test_health_probes_remain_lightweight_and_rate_limit_exempt():
    text = read('app/routes/health.py')
    assert "@health_bp.get('/live')" in text
    assert "@health_bp.get('/ready')" in text
    assert "@limiter.exempt" in text
    live_source = text.split("def live():", 1)[1].split("@health_bp.get('/ready')", 1)[0]
    assert 'db.session.execute' not in live_source


def test_no_obvious_dynamic_code_execution_in_application_sources():
    suspicious = []
    for root in ('app', 'scripts'):
        for path in (ROOT / root).rglob('*.py'):
            text = path.read_text(encoding='utf-8')
            if 'eval(' in text or 'exec(' in text or 'os.system(' in text:
                suspicious.append(str(path.relative_to(ROOT)))
    assert suspicious == []


def test_release_review_keeps_absolute_financial_integrity_rules():
    matrix = read('docs/PDP_COMPLIANCE_MATRIX.md')
    review = read('docs/FINAL_SECURITY_REVIEW.md')
    for phrase in (
        'Never trust client-supplied totals',
        'No expense payment before approval.',
        'Every finalized payment must create exactly one corresponding ledger transaction.',
        'Audit history is append-only and tamper-evident',
    ):
        assert phrase in matrix
    assert 'financial integrity' in review.lower()
