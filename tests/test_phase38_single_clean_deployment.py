from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_single_clean_deployment_policy_exists_and_has_release_boundaries():
    text = read("docs/SINGLE_CLEAN_DEPLOYMENT_POLICY.md")
    required = [
        "Phase 37 Release Gate is PASS",
        "exact release-gated `main` SHA",
        "canonical `server.py` entrypoint",
        "PostgreSQL",
        "Supabase object storage is private",
        "Razorpay production configuration",
        "Persistent shared Redis",
        "HTTPS and secure session cookies",
        "Debug mode is disabled",
        "only the required database migrations",
        "Phase 39",
        "Phase 38 remains open",
        "A repository-only CI pass is insufficient for Phase 38 PASS",
    ]
    for marker in required:
        assert marker in text


def test_deployment_architecture_and_vercel_target_are_canonical():
    architecture = read("docs/DEPLOYMENT_ARCHITECTURE.md")
    vercel = read("vercel.json")
    pyproject = read("pyproject.toml")

    # server.py remains the documented application boundary, while Vercel
    # resolves the Flask application through the canonical module entrypoint.
    assert "server.py" in architecture
    assert 'entrypoint = "app.server:app"' in pyproject
    assert "includeFiles" in vercel
    assert "app/templates/public/*.html" in vercel


def test_deployment_policy_does_not_claim_live_success():
    text = read("docs/SINGLE_CLEAN_DEPLOYMENT_POLICY.md")
    assert "live application changed" in text
    assert "Phase 38 is PASS only when" in text
    assert "actually been deployed" in text


def test_deployment_policy_blocks_manual_production_hot_patching():
    text = read("docs/SINGLE_CLEAN_DEPLOYMENT_POLICY.md")
    assert "Do not make application/configuration edits directly in the production deployment" in text
    assert "Do not hot-patch production files outside source control" in text
