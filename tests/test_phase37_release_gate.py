from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs" / "PDP_COMPLIANCE_MATRIX.md"
POLICY = ROOT / "docs" / "RELEASE_GATE_POLICY.md"


def test_release_gate_policy_exists_and_is_explicit():
    text = POLICY.read_text(encoding="utf-8")
    required = [
        "PDP phase:",
        "Deployment is prohibited",
        "Authentication and session security",
        "Financial ledger integrity",
        "Razorpay order/payment verification",
        "Webhook signature verification",
        "Private document storage",
        "Shared persistent production rate limiting",
        "Exact-HEAD verification",
        "Synthetic CI values prove configuration semantics only",
        "Automatic release blockers",
        "A PASS authorizes proceeding to Phase 38 only",
    ]
    for marker in required:
        assert marker in text


def test_matrix_has_no_unreached_implementation_phase_before_release_gate():
    text = MATRIX.read_text(encoding="utf-8")
    phase_rows = text.splitlines()
    for number in range(0, 37):
        matches = [line for line in phase_rows if f"{number}." in line and line.startswith("|")]
        assert matches, f"missing PDP phase {number} from matrix"
        assert "⚪" not in matches[0], f"phase {number} is unreached before release gate"


def test_matrix_preserves_release_and_financial_boundaries():
    text = MATRIX.read_text(encoding="utf-8")
    required = [
        "This is an engineering implementation matrix, not a legal, statutory, accounting, or security certification.",
        "Absolute financial integrity rules",
        "36. Final Security Review",
        "37. Release Gate",
        "38. Single Clean Deployment",
        "39. Post-Deployment Verification",
        "40. PWA",
    ]
    for marker in required:
        assert marker in text


def test_release_gate_does_not_claim_live_evidence_from_ci():
    text = POLICY.read_text(encoding="utf-8")
    assert "Live production connectivity is" not in text
    assert "do not prove live" in text.lower()
    assert "live payment" in text.lower()
    assert "post-deployment" in text.lower()


def test_release_gate_blocks_unsafe_production_modes():
    text = POLICY.read_text(encoding="utf-8")
    for marker in [
        "SQLite",
        "mock payments",
        "public storage",
        "memory-only production rate limiting",
        "Missing Razorpay webhook secret",
        "Missing Redis provider identity",
        "Debug mode enabled in production",
        "Insecure session cookies in production",
    ]:
        assert marker in text
