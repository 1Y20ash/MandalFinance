# MandalFinance PDP Master Audit

Status: Phase 1 — repository audit initiated
Branch: `pdp-audit`

## Rule
No production deployment or major architectural/security/financial/database changes until the audit and remediation gates are satisfied.

## Framework
- Digital Personal Data Protection Act, 2023
- Digital Personal Data Protection Rules, 2025
- OWASP-oriented application security review
- Financial/payment integrity review

## Audit scope
- Architecture and entrypoint
- Configuration and secrets
- Authentication and authorization
- Personal-data inventory and minimisation
- Privacy notice and consent
- Data Principal rights
- Retention and deletion
- Financial integrity and ledger
- Razorpay/payment/webhook security
- Document upload/download/storage security
- Supabase private storage
- Audit logging
- CSRF/XSS/injection/IDOR/path traversal/SSRF/open redirects
- Rate limiting
- Database and migrations
- Dependencies
- CI/test suite
- Vercel deployment architecture
- Health/readiness checks
- Public transparency exposure

## Initial findings

### CRITICAL
- Duplicate Razorpay webhook implementations require one authoritative payment-event path and database-backed idempotency.

### HIGH
- CI workflow references obsolete `app.py` while current entrypoint is `server.py`.
- Vercel template-copy workaround couples application structure to deployment packaging.
- Payment event idempotency requires a formal database invariant and regression tests.
- Audit records include personal data (email/IP/user-agent/free-form details) and require minimisation/retention review.
- Public donation collection of name/phone/email requires purpose, notice, lawful-basis/consent, access and retention controls.
- Donor/financial records include additional personal data such as address/PAN and require explicit access/retention analysis.
- Document/evidence-pack access requires object-level authorization verification and tests.
- Evidence manifests expose generator identity and need privacy review.

### MEDIUM
- Login `next` handling should use robust same-origin validation rather than a simple prefix check.
- Production readiness/configuration must fail closed when payment/webhook configuration is incomplete.
- SQLite development/testing versus PostgreSQL production requires clean migration and cross-database verification.
- Authentication and registration flows require privacy, enumeration and audit-data review.

## Remediation order
1. Finish repository audit.
2. Finalise defect register and data inventory.
3. Fix architecture/CI/deployment coupling.
4. Consolidate payment/webhook processing and enforce idempotency.
5. Harden auth/RBAC/document authorization.
6. Implement privacy notice, consent/rights/retention/deletion controls as applicable.
7. Minimise audit/log data.
8. Complete security hardening.
9. Expand automated tests and CI release gates.
10. Perform clean production simulation.
11. Deploy only after release gate passes.

## Deployment freeze
No production deployment from this branch until the release gate is explicitly satisfied.
