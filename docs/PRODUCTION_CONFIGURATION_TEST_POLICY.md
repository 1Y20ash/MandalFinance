# Production Configuration Test Policy

## Purpose

Phase 32 verifies that MandalFinance can be configured for production without silently falling back to development, local, mock, or process-local infrastructure.

This is an engineering readiness control, not a production deployment or legal certification.

## Required production boundaries

The production configuration must enforce all of the following:

- PostgreSQL is the database backend; SQLite is rejected.
- `SECRET_KEY` is explicitly supplied by the deployment environment.
- Supabase is configured with a server-side service-role key.
- Supabase document storage remains private.
- Razorpay is the only permitted production payment driver; the mock gateway is rejected.
- Razorpay key ID, key secret, and webhook secret are configured.
- Rate limiting uses persistent shared storage; `memory://` is rejected.
- A non-secret Redis provider identity is recorded for the processor register.
- Production debug mode is disabled.
- Secure session cookies are enabled.
- Configuration validation is fail-closed when a required control is missing or unsafe.

## Test layers

1. **Static configuration review** — inspect configuration, deployment settings, and environment examples for production boundaries.
2. **Configuration preflight** — execute `scripts/verify_production_config.py` using production-shaped non-production credentials and infrastructure identifiers.
3. **Negative-path simulation** — intentionally remove or weaken one control at a time and require validation to fail.
4. **CI enforcement** — the production configuration simulation runs before migration and regression gates.
5. **Clean PostgreSQL verification** — production-shaped configuration is accompanied by the repository's clean PostgreSQL migration verification.

## Secret-handling rule

CI uses synthetic test values only. Real production secrets, service-role keys, payment secrets, Redis credentials, and provider credentials must never be committed to the repository, test fixtures, logs, or documentation.

## Operational production verification

Before a real production release, the deployment operator must verify the actual environment values and provider configuration through the hosting platform's secret/configuration controls. The repository tests deliberately do not connect to or print real third-party credentials.

The actual production Redis provider, region/location where relevant, Supabase project/storage configuration, Razorpay production account, and contractual processor evidence must be recorded in the processor register without recording secret values.

## Release rule

Phase 32 cannot be marked PASS from a single successful happy-path test. The valid configuration must pass and the principal unsafe alternatives must fail closed. The exact committed `main` HEAD must also pass the complete GitHub Actions security workflow.
