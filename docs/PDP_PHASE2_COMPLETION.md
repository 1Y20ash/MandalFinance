# PDP Phase 2 — Remediation / Hardening

Status: **Implemented; verification gate pending**

## Controls completed

- Production Razorpay configuration requires API key, API secret, webhook secret and receiving account.
- Duplicate legacy Razorpay webhook route removed; `/webhooks/razorpay` is authoritative.
- Razorpay webhook signatures are verified against the raw request body.
- Razorpay webhook event IDs are persisted with a provider/event uniqueness constraint for idempotent delivery handling.
- Online donation confirmation serializes the donation row under PostgreSQL row locking to prevent concurrent duplicate ledger posting.
- Gateway order IDs and payment IDs are unique at the database/model layer.
- Public donation creation and payment confirmation are rate limited.
- Public donation flow requires acknowledgement of the standalone privacy notice.
- Post-login redirects reject external and protocol-relative targets.
- Document references and evidence-pack references use UUID-derived identifiers rather than `COUNT()+1`.
- Document upload/replacement persistence is atomic; newly uploaded storage objects are cleaned up if the database transaction fails.
- Evidence-pack manifests no longer include the generating user's email address.
- Non-admin document listing/view/download/replace/verify operations are restricted to the document owner.
- Security headers are applied centrally, including HSTS in production.
- Generic HTTP/unhandled-error responses avoid exposing application internals.
- Audit-log free-form fields are bounded.
- Configurable audit retention is implemented with a controlled Flask CLI command.
- Production retention configuration has safety minimums.
- CI provisions PostgreSQL and Redis, compiles the application, applies migrations and runs the regression/security suite.

## Remaining verification gate

Phase 2 is not considered released until the clean PostgreSQL migration and complete automated test suite pass on `pdp-remediation`.

Production deployment remains frozen until that gate passes and the release is explicitly approved.

## Important scope note

This is an engineering hardening milestone, not legal certification. The notified DPDP Rules, 2025 have a phased commencement schedule, so the implementation is designed to be ready ahead of the applicable operational requirements.
