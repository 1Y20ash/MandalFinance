from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'docs' / 'PUBLIC_TRANSPARENCY_POLICY.md'
TEMPLATE = ROOT / 'app' / 'templates' / 'public' / 'transparency.html'
ROUTE = ROOT / 'app' / 'routes' / 'public.py'


def test_public_transparency_policy_exists_and_defines_boundary():
    text = POLICY.read_text(encoding='utf-8')
    required = [
        'Publicly disclosed information',
        'Information that must never be publicly disclosed',
        'donor names, phone numbers, email addresses',
        'payment gateway secrets',
        'uploaded document contents',
        'audit-log entries',
        'Financial integrity and accuracy',
        'Review and change control',
    ]
    for marker in required:
        assert marker in text


def test_public_transparency_template_is_aggregate_only():
    text = TEMPLATE.read_text(encoding='utf-8').lower()
    forbidden = [
        'donor_name',
        'donor_phone',
        'donor_email',
        'password',
        'session_id',
        'session_cookie',
        'csrf_token',
        'gateway_signature',
        'gateway_payment_id',
        'audit_log',
        'document_url',
        'signed_url',
        'ip_address',
    ]
    for marker in forbidden:
        assert marker not in text


def test_public_transparency_route_only_supplies_aggregate_financial_summary():
    text = ROUTE.read_text(encoding='utf-8')
    start = text.index("@public_bp.route('/transparency')")
    end = text.index("@public_bp.route('/donate'", start)
    route = text[start:end]
    assert "summary=summary" in route
    assert "mandal=mandal" in route
    assert "active_event=active_event" in route
    assert 'Donation.query' in route  # aggregate count is acceptable for internal rendering only
    assert 'donor_email' not in route
    assert 'donor_phone' not in route
    assert 'gateway_' not in route
    assert 'AuditLog' not in route


def test_policy_requires_authoritative_ledger_source():
    text = POLICY.read_text(encoding='utf-8')
    assert 'authoritative ledger' in text
    assert 'client-supplied amount' in text
    assert 'fail closed' in text
