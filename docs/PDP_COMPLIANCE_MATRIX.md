# MandalFinance PDP Compliance Matrix

**Authoritative PDP:** Final DPDP Compliance & Production Readiness Plan  
**Baseline:** `main`  
**Principle:** Money → Transaction → Supporting Document → User → Approval → Payment → Audit History

This is an engineering implementation matrix, not a legal, statutory, accounting, or security certification.

## Current authoritative phase evidence

| PDP phase | Current state | Evidence in repository | Remaining work | Priority |
|---|---|---|---|---|
| 0. Freeze current system | 🟢 | Preserved `main` history and incremental hardening commits | Maintain baseline discipline | P0 |
| 1. Complete repository audit | 🟢/🟡 | Existing security/financial hardening tests and documented architecture evidence | Continue repository-wide defect tracking as later phases expose gaps | P0 |
| 2. Clean architecture | 🟢/🟡 | Flask factory, app package, routes/services/models split, `server.py` entrypoint | Continue removing legacy structural inconsistencies only when verified | P0 |
| 3. Configuration security | 🟢 | Production validation for PostgreSQL, private Supabase storage, Razorpay and persistent rate-limit storage | Verify actual production environment values without exposing secrets | P0 |
| 4. Personal data inventory | 🟡 | Existing models and privacy/security documentation | Complete field-level inventory | P0 |
| 5. Data minimisation | 🟡 | Existing collection paths audited during security work | Complete necessity review for every personal-data field | P0 |
| 6. Privacy Notice | 🟡 | Privacy work tracked in repository | Complete standalone notice and verification | P0 |
| 7. Consent Management | 🟡 | No false PASS asserted | Implement applicable consent evidence and withdrawal workflow | P0 |
| 8. Data Principal Rights | 🟡 | No false PASS asserted | Implement controlled privacy-request workflow | P0 |
| 9. Authentication | 🟢/🟡 | Flask-Login, secure sessions, login rate limiting, generic login failures | Complete password-reset coverage if that feature is introduced | P0 |
| 10. Authorization | 🟢/🟡 | Dynamic RBAC and server-side permission guards | Continue object-level authorization coverage | P0 |
| 11. Financial Integrity | 🟢/🟡 | Central ledger, transaction controls, audit trail and financial guards | Continue full negative-path verification | P0 |
| 12. Payment Security | 🟢/🟡 | Server-side Razorpay verification and protected confirmation flow | Complete production payment simulation | P0 |
| 13. Webhook Security | 🟢/🟡 | Signature verification and duplicate-safe financial confirmation | Complete production webhook simulation | P0 |
| 14. Document Security | 🟢/🟡 | MIME/signature validation, protected storage access, controlled downloads, integrity verification | Complete production object-authorization verification | P0 |
| 15. Supabase Security | 🟢/🟡 | Private-storage configuration and server-only service key handling | Verify production storage policy | P0 |
| 16. Database | 🟢/🟡 | PostgreSQL migration verification and financial constraints | Continue clean-environment reconstruction testing | P0 |
| 17. Retention | 🟡 | No false PASS asserted | Define category-specific retention schedule | P0 |
| 18. Deletion | 🟡 | No false PASS asserted | Implement deliberate deletion workflow | P0 |
| 19. Logging | 🟢 | Structured/redacted operational logging with request correlation | Continue review as new endpoints are introduced | P0 |
| 20. Audit Log | 🟢 | Immutable, tamper-evident audit records with integrity verification | Add new privileged business events when introduced | P0 |
| 21. Security Controls | 🟢 | CSRF, safe redirects, file validation and related automated controls | Continue OWASP-oriented negative-path expansion | P0 |
| 22. Security Headers | 🟢 | CSP, HSTS in production, browser hardening headers with automated tests | Replace CSP `unsafe-inline` allowances with nonce/hash controls in a future hardening pass | P0 |
| 23. Rate Limiting | 🟢 PASS | Shared persistent production storage enforced; Redis backend selection verified; 300/min global ceiling; endpoint-specific limits; health-probe exemptions; safe 429 UI; automated tests; clean PostgreSQL CI | No Phase 23 implementation gap. Actual production Redis connectivity remains part of Phase 32 production configuration testing | P0 |
| **24. Third-Party Processors** | **🟢 PASS** | `docs/THIRD_PARTY_PROCESSOR_REGISTER.md`; Supabase/Razorpay/Vercel/Redis register; browser CDN disclosure review; disabled-provider categories; minimum-data-sharing rules; production Redis provider identity configuration; automated Phase 24 tests | Record the actual production Redis provider/region and contractual evidence during Phase 32; update register before enabling any new provider | **P0** |
| 25. Data Breach Response | ⚪ | Not yet evaluated as the current phase | Create incident response procedure | P0 |
| 26. Public Transparency | 🟡 | Existing public transparency page | Complete privacy-leakage review | P0 |
| 27. Frontend Privacy | 🟡 | Existing server-rendered UI and PWA assets | Complete browser/client-side data audit | P0 |
| 28. Error Handling | 🟢/🟡 | Generic production-safe error handling and safe 429 response | Complete all exception-path review | P0 |
| 29. Dependency Audit | 🟡 | `requirements.txt` includes Flask-Limiter and Redis support | Complete vulnerability/unused-dependency audit | P0 |
| 30. Testing | 🟢/🟡 | Dedicated regression/security suite and phase-specific tests | Complete remaining privacy/payment/E2E coverage | P0 |
| 31. Clean-Environment Test | 🟢/🟡 | Repeatable CI migration/regression verification | Expand clean-environment scenario matrix | P0 |
| 32. Production Configuration Test | 🟢/🟡 | Production preflight and persistent rate-limit configuration validation | Complete real deployment configuration smoke test | P0 |
| 33. Deployment Architecture | 🟢/🟡 | Minimal Flask production entrypoint and CI verification | Final architecture review before deployment | P0 |
| 34. Health Checks | 🟢/🟡 | Liveness/readiness endpoints; rate-limit exempt probes; production dependency checks | Complete production smoke test | P0 |
| 35. DPDP Compliance Matrix | 🟢/🟡 | This evidence matrix | Keep synchronized with implemented controls | P0 |
| 36. Final Security Review | ⚪ | Not yet final | OWASP/security review after all phases | P0 |
| 37. Release Gate | ⚪ | Not yet reached | All checklist controls must PASS | P0 |
| 38. Single Clean Deployment | ⚪ | Not yet reached | Deploy only after release gate | P0 |
| 39. Post-Deployment Verification | ⚪ | Not yet reached | Execute full production verification | P0 |
| 40. PWA | ⚪ | Deferred by authoritative PDP | Perform only after post-deployment stability | P1 |

## Phase 24 — Third-Party Processor evidence

Phase 24 maintains a repository-controlled register of active and potential third parties. The register records the provider role, data shared or potentially exposed, purpose, storage/location considerations, security/minimisation controls, contract/terms evidence, and operational status.

Current application processors/infrastructure include Supabase for application/database and private object storage, Razorpay for online payment processing, Vercel for application hosting, and a deployment-selected managed Redis service for shared rate-limit state. Razorpay Checkout.js and browser CDN/font resources are separately recorded because browser requests can expose network metadata even though they do not receive MandalFinance application records by design.

The register explicitly records processor categories that are not currently enabled, including email, analytics, advertising/tracking, monitoring, support/chat, and additional payment providers. New third parties must be added to the register before enablement.

Production now requires a non-secret `REDIS_PROVIDER_NAME` so the actual Redis processor can be identified operationally without putting provider identity into source-code assumptions. The exact provider, region, contractual evidence, and live environment configuration remain deployment evidence and are re-verified in PDP Phase 32.

Phase 24 automated tests verify that the register covers active infrastructure, records disabled processor categories, records the Redis provider identity configuration, keeps Razorpay's server-side order payload minimal, keeps Supabase service-role access server-side, and documents Vercel hosting.

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

A phase is not considered complete merely because its normal-path test passes. The implementation gate is:

**PLAN → IMPLEMENT → TEST → FIX → VERIFY → DOCUMENT → NEXT PHASE**

CI must remain green after every hardening batch. A green CI run is evidence that the committed test suite passes; it is not by itself a production compliance certification.
