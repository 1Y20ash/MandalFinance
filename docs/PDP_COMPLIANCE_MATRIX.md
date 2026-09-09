# MandalFinance PDP Compliance Matrix

**Authoritative PDP:** Final DPDP Compliance & Production Readiness Plan  
**Baseline:** `main`  
**Principle:** Money → Transaction → Supporting Document → User → Approval → Payment → Audit History

This is an engineering implementation matrix, not a legal, statutory, accounting, or security certification.

## Current authoritative phase evidence

| PDP phase | Current state | Evidence in repository | Remaining work | Priority |
|---|---|---|---|---|
| 0. Freeze current system | 🟢 | Preserved `main` history and incremental hardening commits | Maintain baseline discipline | P0 |
| 1. Complete repository audit | 🟢/🟡 | Security/financial hardening tests and architecture evidence | Continue defect tracking as later phases expose gaps | P0 |
| 2. Clean architecture | 🟢/🟡 | Flask factory, app package, routes/services/models split, `server.py` entrypoint | Remove legacy inconsistencies only when verified | P0 |
| 3. Configuration security | 🟢 | Production validation for PostgreSQL, private Supabase, Razorpay and persistent rate-limit storage | Verify actual production values without exposing secrets | P0 |
| 4. Personal data inventory | 🟡 | Models and privacy/security documentation | Complete field-level inventory | P0 |
| 5. Data minimisation | 🟡 | Collection paths audited during security work | Complete necessity review for every personal-data field | P0 |
| 6. Privacy Notice | 🟡 | Privacy work tracked in repository | Complete standalone notice and verification | P0 |
| 7. Consent Management | 🟡 | No false PASS asserted | Implement applicable consent evidence and withdrawal workflow | P0 |
| 8. Data Principal Rights | 🟡 | No false PASS asserted | Implement controlled privacy-request workflow | P0 |
| 9. Authentication | 🟢/🟡 | Flask-Login, secure sessions, generic failures, login rate limiting, audit events | Complete password-reset coverage if introduced | P0 |
| 10. Authorization | 🟢/🟡 | RBAC and server-side permission guards | Continue object-level authorization coverage | P0 |
| 11. Financial Integrity | 🟢/🟡 | Central ledger, transaction controls, approval/payment guards, audit trail | Continue full negative-path verification | P0 |
| 12. Payment Security | 🟢/🟡 | Server-side Razorpay verification and protected confirmation flow | Complete production payment simulation | P0 |
| 13. Webhook Security | 🟢/🟡 | Signature verification and duplicate-safe confirmation | Complete production webhook simulation | P0 |
| 14. Document Security | 🟢/🟡 | MIME/signature validation, private storage, authorization, integrity/version controls | Complete production object-authorization verification | P0 |
| 15. Supabase Security | 🟢/🟡 | Private-storage configuration and server-only service key handling | Verify production storage policy | P0 |
| 16. Database | 🟢/🟡 | PostgreSQL migrations and financial constraints | Continue clean-environment reconstruction testing | P0 |
| 17. Retention | 🟡 | No false PASS asserted | Define category-specific retention schedule | P0 |
| 18. Deletion | 🟡 | No false PASS asserted | Implement deliberate deletion workflow | P0 |
| 19. Logging | 🟢 | Structured/redacted operational logs with request correlation | Review new endpoints as introduced | P0 |
| 20. Audit Log | 🟢 | Immutable, tamper-evident audit records with integrity verification | Add new privileged business events when introduced | P0 |
| 21. Security Controls | 🟢 | CSRF, safe redirects, file validation and related controls | Continue OWASP negative-path expansion | P0 |
| 22. Security Headers | 🟢 | CSP, HSTS in production and browser hardening headers | Replace CSP `unsafe-inline` with nonce/hash controls in future hardening | P0 |
| 23. Rate Limiting | 🟢 PASS | Shared persistent production storage, endpoint-specific limits, safe 429 UI, automated tests and clean PostgreSQL CI | Actual production Redis connectivity remains environment evidence | P0 |
| 24. Third-Party Processors | 🟢 PASS | Processor register for Supabase/Razorpay/Vercel/Redis/CDNs; minimum-data-sharing rules and disabled-provider categories | Record actual production provider/region/contract evidence before enabling changes | P0 |
| 25. Data Breach Response | 🟢 PASS | Formal detection-through-review lifecycle, severity, escalation, evidence preservation and notification workflow | Validate operational contacts/channels before production | P0 |
| 26. Public Transparency | 🟢 PASS | Aggregate-only transparency policy, route/template boundary tests and authoritative-ledger disclosure rules | Re-review when public disclosures change | P0 |
| 27. Frontend Privacy | 🟢 PASS | Browser storage boundary, session-only UI state, service-worker restrictions and donation CSRF precache exclusion | Re-review when browser storage/SDK/offline behavior changes | P0 |
| 28. Error Handling | 🟢 PASS | Generic HTML/JSON errors, privacy-safe 500 handling, DB rollback, safe health errors and regression tests | Re-review new API/error classes/integrations | P0 |
| 29. Dependency Audit | 🟢 PASS | `pip-audit==2.10.1` strict CI gate against resolved environment plus dependency policy/tests | Re-audit on every dependency change | P0 |
| 30. Testing | 🟢 PASS | Layered strategy, critical regression inventory, cryptographic payment/webhook negative paths and clean PostgreSQL CI | Expand coverage as capabilities evolve | P0 |
| 31. Clean-Environment Test | 🟢 PASS | Fresh CI installation, isolated PostgreSQL 16, migration-head check, empty-database migration and full regression suite | Keep mandatory regression gate | P0 |
| 32. Production Configuration Test | 🟢 PASS | Fail-closed PostgreSQL/Razorpay/private-Supabase/persistent-Redis validation, unsafe simulations and secure-cookie assertions | Verify actual production values without exposing secrets; smoke test in Phase 39 | P0 |
| 33. Deployment Architecture | 🟢 PASS | Canonical `server.py`, Vercel boundary, PostgreSQL/Supabase/Redis/Razorpay state boundaries, migration ownership and server-side authorization | Validate actual deployed topology later | P0 |
| 34. Health Checks | 🟢 PASS | `/health/live`, DB-backed `/health/ready` with safe 503, backward-compatible `/health`, safe logging and rate-limit exemption | Validate live probes in Phase 39 | P0 |
| 35. DPDP Compliance Matrix | 🟢 PASS | Authoritative matrix plus governance policy, traceability, evidence/environment/legal boundaries and downgrade rules; automated tests | Keep synchronized with material control changes | P0 |
| 36. Final Security Review | 🟢 PASS | Cross-cutting review, negative-path inventory, CSP hardening note and automated review tests | Live production evidence remains Phases 38–39 | P0 |
| **37. Release Gate** | **🟢 PASS** | `docs/RELEASE_GATE_POLICY.md`; independent release-blocker checklist; exact-HEAD requirement; production prerequisite boundaries; automated Phase 37 gate tests; exact-head GitHub Actions success | Proceed to Phase 38 only; do not infer live production health | **P0** |
| **38. Single Clean Deployment** | **🟢/🟡** | `docs/SINGLE_CLEAN_DEPLOYMENT_POLICY.md`; deployment-sequence and anti-hot-patch controls; dedicated Phase 38 CI tests; canonical Vercel/server entrypoint verified | Execute one real production deployment from an exact Phase-37-gated SHA and record non-secret deployment evidence; Vercel deployment remains environment evidence | **P0** |
| 39. Post-Deployment Verification | ⚪ | Not yet reached | Execute full production verification | P0 |
| 40. PWA | ⚪ | Deferred by authoritative PDP | Perform only after post-deployment stability | P1 |

## Phase 37 — Release Gate evidence

Phase 37 establishes `docs/RELEASE_GATE_POLICY.md` as the controlled pre-deployment release gate. It independently requires implemented PDP controls to be evidenced, blocks unresolved P0/P1 defects and unsafe production modes, and distinguishes synthetic CI evidence from live production evidence.

The release gate checks authentication/session security, authorization, CSRF/request integrity, financial ledger integrity, Razorpay verification, webhook security, document security, PostgreSQL/migrations, audit logging, privacy-safe logging/errors, security headers, shared persistent rate limiting, dependency security, frontend privacy, processor governance, breach response, DPDP engineering governance, and health-check implementation.

Production prerequisites include PostgreSQL, private Supabase storage, Razorpay production configuration with webhook secret, persistent shared Redis with provider identity, HTTPS, secure session cookies, disabled debug mode, required environment variables, verified migration state, canonical `server.py` hosting entrypoint, and required health probes. Secrets must never be exposed in repository-controlled client assets.

`tests/test_phase37_release_gate.py` verifies the policy, confirms that phases 0–36 are not unreached, preserves the engineering/non-certification boundary, requires live-production evidence to remain separate from CI claims, and checks principal unsafe-production blockers. The CI workflow runs this dedicated gate before migration and the full regression/security suite.

The Phase 37 PASS authorizes progression to Phase 38 only. It does not claim that production is deployed, that external providers are reachable, or that post-deployment verification has passed.

## Phase 38 — Single Clean Deployment evidence

Phase 38 establishes `docs/SINGLE_CLEAN_DEPLOYMENT_POLICY.md` as the controlled deployment procedure. The repository now enforces the deployment sequence, exact release-gated SHA boundary, canonical `server.py` entrypoint, production prerequisite checklist, controlled migration boundary, deployment evidence requirements, rollback boundary, and prohibition on manual production hot-patching.

`tests/test_phase38_single_clean_deployment.py` verifies these controls and confirms the canonical Vercel/server deployment configuration. The dedicated CI step proves that the deployment policy and configuration are internally consistent; it does **not** claim that a live deployment has succeeded.

Phase 38 therefore remains 🟢/🟡 until one real production deployment is completed from an exact Phase-37-gated SHA and non-secret deployment evidence is recorded. A hosting-provider rejection or rate limit must leave Phase 38 open rather than being represented as a PASS.

## Absolute financial integrity rules

1. Store monetary values as `NUMERIC/DECIMAL`; normalize with Python `Decimal`.
2. Never trust client-supplied totals, status transitions, permissions, identities, or approval state.
3. Never silently delete finalized financial records; use correction/reversal workflows.
4. A finalized document replacement must preserve a version, reason, uploader, timestamp, and SHA-256 hash.
5. No expense payment before approval.
6. No self-approval for normal expense/correction/budget approval workflows.
7. Every finalized payment must create exactly one corresponding ledger transaction.
8. External payment references must not be reusable.
9. Locked events/financial years must reject financial mutations.
10. Reports, dashboards, account balances, reconciliations, and evidence packs must derive from one authoritative ledger invariant.
11. A reconciliation cannot be finalized while statement lines are unmatched or the balance difference is non-zero.
12. Budget actuals are derived from finalized ledger transactions rather than duplicated module totals.
13. Audit history is append-only and tamper-evident; security-sensitive events must not be silently discarded.

## Verification gate

A phase is not complete merely because its normal-path test passes. The implementation gate is:

**PLAN → IMPLEMENT → TEST → FIX → VERIFY → DOCUMENT → NEXT PHASE**

CI must remain green after every hardening batch. A green CI run is evidence that the committed test suite passes; it is not by itself a production compliance certification.
