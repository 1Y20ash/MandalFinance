from pathlib import Path


def _procedure():
    return Path('docs/DATA_BREACH_RESPONSE_PROCEDURE.md').read_text(encoding='utf-8')


def test_breach_response_procedure_contains_required_lifecycle():
    procedure = _procedure()
    required = (
        'DETECT', 'INVESTIGATE', 'CONTAIN', 'ASSESS',
        'IDENTIFY AFFECTED DATA', 'DOCUMENT', 'NOTIFY WHERE REQUIRED',
        'REMEDIATE', 'REVIEW',
    )
    for stage in required:
        assert stage in procedure


def test_breach_response_procedure_preserves_investigation_evidence_without_secrets():
    procedure = _procedure()
    for evidence in ('request/correlation IDs', 'audit event IDs', 'deployment/commit identifiers'):
        assert evidence in procedure
    assert 'Do not put passwords, access tokens' in procedure
    assert 'Do not copy production databases' in procedure
    assert 'request bodies, query strings, cookies, authorization headers' in procedure


def test_breach_response_procedure_covers_financial_and_document_impact():
    procedure = _procedure()
    for category in ('Financial/application data', 'Supporting documents', 'Payment data'):
        assert category in procedure
    assert 'Do not silently rewrite finalized records' in procedure
    assert 'correction/reversal' in procedure


def test_breach_response_procedure_has_dpdp_notification_guardrails():
    procedure = _procedure()
    assert 'Digital Personal Data Protection Rules, 2025' in procedure
    assert 'notify the Data Protection Board without delay' in procedure
    assert 'within 72 hours' in procedure
    assert 'applicable commencement/enforcement timeline must be checked' in procedure
    assert 'current-rule verification requirement' in procedure


def test_breach_response_procedure_covers_processors_and_post_incident_testing():
    procedure = _procedure()
    for provider in ('Supabase', 'Razorpay', 'Vercel', 'Redis'):
        assert provider in procedure
    assert 'add regression tests reproducing the incident' in procedure
    assert 'post-incident review' in procedure.lower()
    assert 'retention/destruction requirement' in procedure.lower()
