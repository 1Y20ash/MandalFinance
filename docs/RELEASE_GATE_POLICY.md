# MandalFinance Release Gate Policy

**PDP phase:** 37 — Release Gate  
**Purpose:** independent pre-deployment gate for the final `main` state.

This gate is an engineering release-control mechanism. It is not a legal, statutory, accounting, penetration-test, or DPDP certification.

## Gate rule

Deployment is prohibited unless every required PDP control is either:

- **PASS** with repository and CI evidence; or
- explicitly identified by the PDP as **environment-specific and required before deployment**, with a concrete verification owner/evidence path.

Unreached implementation phases, unresolved P0/P1 defects, weakened financial-integrity controls, unsafe production configuration, missing required secrets/configuration, or documentation-only claims of live evidence block release.

## Required pre-deployment controls

### Implementation controls

- Authentication and session security
- Authorization and object-level access control
- CSRF/request integrity
- Financial ledger integrity and approval controls
- Razorpay order/payment verification
- Webhook signature verification and duplicate handling
- Private document storage, authorization, validation and integrity controls
- PostgreSQL migrations and constraints
- Immutable/tamper-evident audit logging
- Privacy-safe operational logging and error handling
- Security headers and browser protections
- Shared persistent production rate limiting
- Dependency security audit
- Frontend privacy/cache boundaries
- Third-party processor register
- Breach-response procedure
- DPDP engineering matrix and traceability
- Health-check implementation

### Production prerequisites

Before the single clean deployment, the release owner must verify without exposing secrets:

1. PostgreSQL is the production database.
2. Supabase object storage is private.
3. Razorpay production configuration is selected and webhook secret is configured.
4. Persistent shared Redis is configured for rate limiting and its provider identity is recorded.
5. HTTPS and secure session-cookie settings are active.
6. Debug mode is disabled.
7. Required environment variables are present and no credentials are committed to the repository.
8. Database migrations have a single expected head and can be applied cleanly.
9. Hosting uses the canonical `server.py` application entrypoint.
10. Required health probes are available.

## Exact-HEAD verification

The release decision applies only to the exact commit that will be deployed. GitHub Actions must pass on that exact `main` HEAD, including dependency audit, production-configuration simulation, architecture, health, DPDP matrix, migration, and complete regression/security tests.

If a subsequent commit changes application, configuration, migration, workflow, security documentation, or release-gate evidence, the gate must be re-evaluated and CI must pass again on the new exact HEAD.

## Environment-evidence boundary

Synthetic CI values prove configuration semantics only. They do not prove live payment, webhook delivery, Redis connectivity, Supabase object authorization, hosting topology, or production health. Those are explicitly verified during the deployment and post-deployment phases.

## Automatic release blockers

- Any failed required CI check
- Any unresolved P0/P1 security or financial-integrity defect
- Any phase falsely represented as PASS
- SQLite, mock payments, public storage, or memory-only production rate limiting
- Missing Razorpay webhook secret
- Missing Redis provider identity
- Debug mode enabled in production
- Insecure session cookies in production
- Unverified database migration state
- Secrets exposed in repository-controlled client assets
- Live production evidence claimed solely from synthetic CI

## Gate outcome

Phase 37 is PASS only after this policy, the automated Phase 37 gate tests, the current PDP matrix, and the exact final `main` CI result all agree. The gate must identify the exact commit SHA and CI run used for the decision.

A PASS authorizes proceeding to Phase 38 only; it does not itself perform deployment or claim post-deployment health.
