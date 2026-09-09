from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / 'docs' / 'PDP_COMPLIANCE_MATRIX.md'
POLICY = ROOT / 'docs' / 'DPDP_COMPLIANCE_MATRIX_POLICY.md'


def test_phase35_matrix_and_policy_exist():
    assert MATRIX.is_file()
    assert POLICY.is_file()


def test_phase35_matrix_has_authoritative_status_and_release_boundaries():
    text = MATRIX.read_text(encoding='utf-8')
    required = [
        'Authoritative PDP',
        'Verification gate',
        'Absolute financial integrity rules',
        '35. DPDP Compliance Matrix',
        '36. Final Security Review',
        '37. Release Gate',
        '38. Single Clean Deployment',
        '39. Post-Deployment Verification',
        '40. PWA',
        'This is an engineering implementation matrix, not a legal, statutory, accounting, or security certification.',
    ]
    for marker in required:
        assert marker in text, marker


def test_phase35_matrix_preserves_existing_phase_evidence_and_boundaries():
    text = MATRIX.read_text(encoding='utf-8')
    for marker in [
        '24. Third-Party Processors',
        '25. Data Breach Response',
        '26. Public Transparency',
        '27. Frontend Privacy',
        '28. Error Handling',
        '29. Dependency Audit',
        '30. Testing',
        '31. Clean-Environment Test',
        '32. Production Configuration Test',
        '33. Deployment Architecture',
        '34. Health Checks',
        'No expense payment before approval.',
        'Every finalized payment must create exactly one corresponding ledger transaction.',
        'Audit history is append-only and tamper-evident',
    ]:
        assert marker in text, marker


def test_phase35_policy_defines_traceability_and_non_certification_boundary():
    text = POLICY.read_text(encoding='utf-8')
    required = [
        'authoritative engineering index',
        '🟢 PASS',
        '🟢/🟡',
        'Required traceability',
        'implementation files, routes, services, models, configuration, or infrastructure boundaries',
        'automated tests and the CI gate',
        'Environment-specific evidence belongs to the PDP phase that explicitly owns it',
        'must not be presented as proof of live production connectivity or deployment behavior',
        'legal applicability',
        'commencement timing',
        'contractual interpretation',
        'regulatory advice',
        'Release Gate',
    ]
    for marker in required:
        assert marker in text, marker


def test_phase35_policy_requires_downgrade_when_later_work_exposes_a_defect():
    text = POLICY.read_text(encoding='utf-8')
    assert 'downgrade the affected phase' in text
    assert 'restore PASS only after exact-head CI verification' in text
    assert 'Do not mark a phase PASS merely because a documentation file exists.' in text
