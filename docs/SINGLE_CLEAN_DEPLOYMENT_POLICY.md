# MandalFinance Single Clean Deployment Policy

**PDP phase:** 38 — Single Clean Deployment  
**Purpose:** define and enforce the one controlled production deployment after the Phase 37 release gate.

This policy is an engineering deployment-control mechanism. It is not a legal, statutory, accounting, penetration-test, or DPDP certification.

## Deployment rule

Production must be deployed once from one explicitly identified, release-gated `main` commit. Deployment must not be assembled by manually mixing files, configuration, migrations, or artifacts from different commits.

The deployment target must use the canonical `server.py` entrypoint and the production architecture documented in `docs/DEPLOYMENT_ARCHITECTURE.md`.

## Pre-deployment conditions

Before deployment:

1. Phase 37 Release Gate is PASS for the exact commit.
2. Required GitHub Actions checks pass for that exact commit.
3. Production configuration is prepared without exposing secrets.
4. PostgreSQL is the production database.
5. Supabase object storage is private.
6. Razorpay production configuration and webhook secret are configured.
7. Persistent shared Redis is configured and its provider identity is recorded.
8. HTTPS and secure session cookies are active.
9. Debug mode is disabled.
10. The expected migration head is known and migration execution is controlled.
11. No repository-controlled client asset contains provider secrets.
12. The production hostname and deployment target are explicitly identified.

## Clean deployment sequence

The release owner must:

1. Identify the exact release-gated `main` SHA.
2. Confirm the SHA has passed the required CI workflow.
3. Confirm production environment prerequisites without exposing secret values.
4. Deploy that exact SHA through the approved hosting/deployment mechanism.
5. Apply only the required database migrations for that release, using the controlled migration process.
6. Record deployment timestamp, commit SHA, deployment identifier, migration result, and non-secret environment evidence.
7. Do not make application/configuration edits directly in the production deployment after release.
8. Hand off immediately to Phase 39 for live verification.

## Single-deployment boundary

A failed or incomplete deployment is not evidence of a successful deployment. If the hosting provider rejects or rate-limits the deployment, Phase 38 remains open. Do not mark the phase PASS by treating a source commit, CI success, or deployment configuration as proof that the live application changed.

If a new application/configuration/migration/security change is committed after the release-gated SHA, the new SHA requires the release gate and CI again before deployment.

## Rollback boundary

If deployment causes a verified release-blocking production fault, use the hosting provider's controlled rollback to the last known-good release and record the incident. Do not hot-patch production files outside source control. Any corrective code change must return through the normal release gate.

## Evidence boundary

Repository tests prove deployment semantics and release discipline. They do not prove that a live hosting provider accepted the deployment, that the live hostname serves the new SHA, or that production dependencies are reachable. Those facts belong to Phase 39.

## Phase outcome

Phase 38 is PASS only when:

- one exact release-gated commit has actually been deployed;
- the deployment identifier and commit SHA are recorded;
- controlled migrations completed successfully, if required; and
- there is sufficient non-secret deployment evidence to hand off to Phase 39.

A repository-only CI pass is insufficient for Phase 38 PASS.
