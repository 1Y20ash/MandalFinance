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
| **25. Data Breach Response** | **🟢 PASS** | `docs/DATA_BREACH_RESPONSE_PROCEDURE.md`; formal incident lifecycle; severity/escalation; evidence-preservation rules; affected-data assessment; DPDP notification workflow; processor escalation; remediation/review controls; automated Phase 25 documentation tests | Validate operational contacts and notification channels before production; keep procedure aligned with applicable law and provider terms | P0 |
| **26. Public Transparency** | **🟢 PASS** | `docs/PUBLIC_TRANSPARENCY_POLICY.md`; public transparency route reviewed as aggregate-only; public template checked for sensitive-field leakage; authoritative-ledger disclosure boundary; automated Phase 26 tests | Re-review public disclosures whenever financial, payment, document, or personal-data processing changes | **P0** |
| **27. Frontend Privacy** | **🟢 PASS** | `docs/FRONTEND_PRIVACY_POLICY.md`; browser storage boundary; PWA session-only UI state; donation CSRF token excluded from service-worker precache; service-worker GET/same-origin/static/public-shell restrictions; automated Phase 27 tests | Re-review whenever browser storage, SDKs, offline behavior, payment/document flows, or tracking changes | **P0** |
| **28. Error Handling** | **🟢 PASS** | `docs/ERROR_HANDLING_POLICY.md`; generic HTML/JSON handling for expected HTTP errors; privacy-safe 500 handling with server-side logging and DB rollback; health-error detail suppression; automated Phase 28 regression tests | Re-review when new API surfaces, error classes, or external integrations are introduced | **P0** |
| **29. Dependency Audit** | **🟢 PASS** | `docs/DEPENDENCY_SECURITY_POLICY.md`; clean CI dependency installation; exact `pip-audit==2.10.1` security gate against `requirements.txt`; Phase 29 dependency-policy regression tests | Re-audit on every dependency change and remediate newly disclosed vulnerabilities | **P0** |
| **30. Testing** | **🟢 PASS** | `docs/TESTING_STRATEGY.md`; layered unit/service, route/integration, persistence, security, privacy, and critical-flow testing policy; automated Phase 30 test-inventory gate; payment/webhook cryptographic negative-path tests; public payment failure non-disclosure regression; clean CI PostgreSQL and full pytest gate | Expand scenario coverage as new privacy, payment, document, or E2E capabilities are introduced; production simulations remain in later PDP phases | **P0** |
| **31. Clean-Environment Test** | **🟢 PASS** | Repeatable fresh-checkout CI dependency installation; isolated PostgreSQL 16 service; migration-head verification; database creation and migration from an empty database; complete regression/security suite; cleanup/teardown | Continue using clean-environment verification as a mandatory regression gate | **P0** |
| **32. Production Configuration Test** | **🟢 PASS** | `docs/PRODUCTION_CONFIGURATION_TEST_POLICY.md`; fail-closed PostgreSQL/Razorpay/private-Supabase/persistent-Redis validation; synthetic production-shaped preflight; negative-path configuration simulations; secure-cookie assertions; CI-enforced dedicated Phase 32 test gate | Record actual production provider/region/configuration evidence without exposing secrets; perform final production smoke test in Phase 39 | **P0** |
| 33. Deployment Architecture | 🟢/🟡 | Minimal Flask production entrypoint and CI verification | Final architecture review before deployment | P0 |
| 34. Health Checks | 🟢/🟡 | Liveness/readiness endpoints; rate-limit exempt probes; production dependency checks | Complete production smoke test | P0 |
| 35. DPDP Compliance Matrix | 🟢/🟡 | This evidence matrix | Keep synchronized with implemented controls | P0 |
| 36. Final Security Review | ⚪ | Not yet final | OWASP/security review after all phases | P0 |
| 37. Release Gate | ⚪ | Not yet reached | All checklist controls must PASS | P0 |
| 38. Single Clean Deployment | ⚪ | Not yet reached | Deploy only after release gate | P0 |
| 39. Post-Deployment Verification | ⚪ | Not yet reached | Execute full production verification | P0 |
| 40. PWA | ⚪ | Deferred by authoritative PDP | Perform only after post-deployment stability | P1 |

## Phase 32 — Production Configuration Test evidence

Phase 32 establishes `docs/PRODUCTION_CONFIGURATION_TEST_POLICY.md` as the controlled production-configuration verification standard. The policy requires PostgreSQL, private Supabase storage, Razorpay, persistent shared rate-limit storage, a recorded Redis provider identity, disabled production debug mode, and secure session cookies. Configuration validation must fail closed when these boundaries are missing or weakened.

The repository now contains `tests/test_phase32_production_configuration.py`. The suite executes the actual production preflight script in isolated subprocesses so configuration is evaluated from fresh environment state rather than relying on imported test-process configuration. It verifies a valid production-shaped configuration and deliberately tests unsafe alternatives: SQLite, the mock payment gateway, public Supabase storage, memory-only rate limiting, missing Redis provider identity, and missing Razorpay webhook secret.

The CI workflow runs the dedicated Phase 32 production-configuration simulation before migration and full regression testing. CI values are synthetic and are never production credentials. This verifies configuration semantics without making external payment, database, Supabase, or Redis connections from the preflight itself.

Actual production provider identity, region/location where relevant, contractual evidence, and final production smoke verification remain environment-specific controls for the later deployment/post-deployment phases; they must not be represented as completed merely from synthetic CI configuration.

## Phase 30 — Testing evidence

Phase 30 establishes `docs/TESTING_STRATEGY.md` as the controlled application testing standard. The strategy defines layered unit/service, route/integration, persistence, security-regression, privacy-regression, and critical-flow testing, with explicit test-isolation and CI-gate requirements.

The repository now enforces a critical regression inventory through `tests/test_phase30_testing.py`. The inventory ensures that authentication, donations, financial controls, ledger/reconciliation, document security, audit logging, operational logging, dependency controls, and the Phase 30 testing controls themselves remain represented by automated test modules.

Phase 30 also adds direct cryptographic negative-path coverage for Razorpay payment signatures and webhook signatures, including tampered payload/payment identifiers and missing signatures. The public online-donation setup path is tested against an injected provider failure to ensure an internal exception string is not returned to the user. The associated route handling was hardened to return generic failure messages and roll back the database session.

The CI workflow remains the mandatory gate: dependency installation and security scanning, compilation, production preflight, migration-head verification, clean PostgreSQL migration, and the complete pytest regression/security suite must all succeed before the phase can close. Production payment simulations and real deployment smoke tests are deliberately deferred to the later PDP phases that own those environments.

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
