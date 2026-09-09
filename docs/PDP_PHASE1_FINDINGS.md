# PDP Phase 1 Findings — Evidence Register

## Critical

### PDP-001 — Duplicate Razorpay webhook processing
**Area:** Payments / financial integrity

Two webhook endpoints/implementations exist in the application. This creates a risk of divergent behaviour, duplicate processing and inconsistent audit/ledger outcomes.

**Required action:** consolidate into one authoritative webhook service/path, introduce a database-level idempotency invariant keyed to the provider event identifier, and add duplicate-event tests.

## High

### PDP-002 — CI references obsolete application entrypoint
The security workflow references `app.py` for compilation and Flask CLI commands while the current application entrypoint is `server.py`.

**Impact:** CI is not a reliable release gate until corrected.

### PDP-003 — Deployment-specific template workaround
The current deployment configuration copies templates into a root directory. This couples application correctness to a packaging workaround and must be reviewed during architecture cleanup.

### PDP-004 — Audit-log personal data
Audit records include identity and request metadata such as email, IP address and user-agent, plus free-form details. These fields require purpose limitation, minimisation, retention and access controls.

### PDP-005 — Public donation personal-data collection
The donation flow collects donor identity/contact information. The final design must establish the purpose, notice, applicable processing basis, retention, rights handling and processor disclosures.

### PDP-006 — Financial records contain personal data
Donation/financial models contain identity/contact/address/PAN and payment-related fields. Access, exports, public transparency and retention must be mapped field-by-field.

### PDP-007 — Document/evidence object authorization
Document operations require explicit object ownership/role checks and regression tests against cross-user access, including evidence-pack generation.

### PDP-008 — Evidence-pack privacy exposure
Evidence-pack manifests include generator identity. Review whether this is necessary and ensure private information is not exposed to recipients who should not receive it.

## Medium

### PDP-009 — Login redirect validation
The login flow accepts a `next` parameter and should use robust same-origin URL validation rather than relying only on a leading slash check.

### PDP-010 — Production payment readiness
Production configuration must fail closed when payment functionality is enabled but required credentials/webhook configuration are incomplete.

### PDP-011 — SQLite/PostgreSQL parity
Development/testing and production database paths differ. Fresh PostgreSQL migration and application tests must remain release-gate checks.

### PDP-012 — Authentication privacy/enumeration review
Registration and authentication responses reveal account-existence information and collect multiple identity fields. Review UX/security/privacy trade-offs and test the final behaviour.

## Phase 1 status
Audit initiated. Remediation is deliberately controlled and will proceed by severity after the repository-wide evidence register is complete.
