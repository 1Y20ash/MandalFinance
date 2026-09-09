from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dependency_manifest_exists_and_is_constrained():
    manifest = ROOT / "requirements.txt"
    assert manifest.exists()

    requirements = [
        line.strip()
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert requirements

    # Every direct dependency must carry an explicit minimum/version constraint.
    # This prevents silently introducing completely unconstrained runtime packages.
    for requirement in requirements:
        assert any(operator in requirement for operator in ("==", ">=", "~=", "<", ">")), requirement


def test_dependency_security_policy_and_ci_audit_are_present():
    policy = ROOT / "docs" / "DEPENDENCY_SECURITY_POLICY.md"
    workflow = ROOT / ".github" / "workflows" / "security-financial-integrity.yml"

    assert policy.exists()
    policy_text = policy.read_text(encoding="utf-8")
    workflow_text = workflow.read_text(encoding="utf-8")

    assert "pip-audit" in policy_text
    assert "pip-audit==2.10.1" in policy_text
    assert "pip-audit==2.10.1" in workflow_text
    assert "pip-audit -r requirements.txt" in workflow_text


def test_dependency_policy_requires_failure_on_known_vulnerabilities():
    policy_text = (ROOT / "docs" / "DEPENDENCY_SECURITY_POLICY.md").read_text(encoding="utf-8")
    assert "must fail the workflow" in policy_text
    assert "silently ignoring scanner output is prohibited" in policy_text
    assert "transitive vulnerabilities are included" in policy_text
