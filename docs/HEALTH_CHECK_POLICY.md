# MandalFinance Health Check Policy

**PDP Phase:** 34 — Health Checks
**Status:** Controlled health-check baseline

## Purpose

Health endpoints provide deployment infrastructure with safe signals about application liveness and required dependency readiness. They must not expose credentials, connection strings, stack traces, exception messages, or other internal infrastructure details.

## Endpoints

### `/health/live`

Liveness is process-level only. A successful HTTP 200 response means the Flask application can accept and serve a request. It deliberately does not query PostgreSQL or other dependencies, so a dependency outage does not cause healthy application processes to be restarted unnecessarily.

### `/health/ready`

Readiness verifies the required PostgreSQL dependency with a minimal `SELECT 1`. It returns HTTP 200 with `READY` when the database is reachable and HTTP 503 with a generic `UNHEALTHY` response when it is not. Database exceptions are logged server-side and never returned to the caller.

### `/health`

The existing endpoint remains as a backward-compatible diagnostic summary. It reports only application status and database health, with no raw exception details.

## Security and privacy rules

- Do not expose database URLs, hostnames, ports, usernames, passwords, tokens, provider keys, stack traces, SQL errors, or filesystem paths.
- Do not include request cookies, authorization headers, query strings, or request bodies in health responses.
- Health probes are exempt from application rate limits so infrastructure can reliably monitor service health.
- Health failures must not silently substitute SQLite, memory-only state, mock payments, or public storage.
- Readiness failure is a deployment signal, not proof that the application process itself is dead.

## Operational contract

Deployment infrastructure should use `/health/live` for liveness and `/health/ready` for readiness. Actual production monitoring and post-deployment verification remain environment-specific evidence and are owned by the later deployment phases.

## Verification

Phase 34 tests verify endpoint status codes, response boundaries, database failure behavior, privacy-safe error handling, and rate-limit exemption. The CI workflow must pass the dedicated health-check gate before migrations and the full regression suite proceed.
