# MandalFinance Testing Strategy

## Purpose

Phase 30 establishes the repeatable testing standard for MandalFinance. The objective is to prove critical security, privacy, financial-integrity, payment, document, and authorization boundaries through automated regression tests rather than relying on manual happy-path checks.

This document is an engineering testing policy, not a legal, accounting, or security certification.

## Test layers

### 1. Unit/service tests

Business services and security helpers are tested directly for deterministic validation, financial arithmetic, rollback behavior, integrity verification, and failure handling.

### 2. Route/integration tests

Flask test-client tests exercise authentication, authorization, CSRF-protected state changes, financial routes, document routes, public transparency, error responses, rate limits, and security headers.

### 3. Persistence tests

Tests verify database invariants, transaction posting, audit records, document metadata, immutable audit behavior, and clean PostgreSQL migration compatibility in CI.

### 4. Security regression tests

Negative-path tests are mandatory for unsafe redirects, unauthorized access, malformed financial values, invalid document types, duplicate payment confirmation, webhook verification, rate-limit exhaustion, sensitive error leakage, and browser security controls where the feature exists.

### 5. Privacy regression tests

Tests must prevent accidental exposure of credentials, authentication/session material, donor personal data, payment secrets, private documents, audit/security telemetry, and internal identifiers through public or browser-facing surfaces.

### 6. End-to-end critical-flow tests

The automated suite must cover the critical business chain at the application boundary: authenticated user → authorized financial action → authoritative ledger mutation → audit evidence, plus payment initiation/confirmation and protected document access where those features are enabled.

External provider calls must be mocked or isolated in CI. Production provider behavior is verified separately in the production-configuration and deployment phases; CI must never require production secrets.

## Mandatory regression areas

The regression suite must retain coverage for:

- authentication success, failure, approval-state blocking, logout, safe redirects, and CSRF
- authorization and object-level access boundaries
- donation/income/expense/contribution financial posting and rollback behavior
- Decimal/NUMERIC monetary handling and ledger invariants
- payment order creation, server-side verification, duplicate/idempotent confirmation, and webhook signature handling
- document upload validation, protected download, integrity verification, and replacement/version controls
- immutable/tamper-evident audit logging and request correlation
- privacy-safe operational errors and health responses
- security headers and browser cache/storage boundaries
- endpoint-specific rate limits and shared production storage configuration
- public transparency aggregate-only disclosure
- third-party processor/minimum-data-sharing controls
- migration-head and clean PostgreSQL reconstruction

## Test isolation

Tests must use isolated fixtures and must not depend on production data, production storage, real payment credentials, or persistent local artifacts. External state used by tests must be reset or namespaced between cases.

The test suite must remain deterministic enough for CI and must not depend on execution order. When shared rate-limit state is deliberately consumed, the fixture must clean that state after the test.

## CI gate

The GitHub Actions `Security and Financial Integrity` workflow is the required automated gate. A phase is not complete if the regression/security job is running or failed. The workflow must perform dependency installation, dependency security scanning, source compilation, production configuration preflight, migration verification, clean PostgreSQL migration, and the complete pytest suite.

The suite is fail-closed: a failing test, import/compile error, migration error, or security-scan failure blocks progression to the next PDP phase.

## Coverage philosophy

Line coverage is useful but is not a substitute for boundary coverage. Priority is given to high-risk behaviors and negative paths. Coverage improvements must focus on security decisions, authorization, money movement, external payment confirmation, document access, privacy boundaries, and failure handling.

When a new sensitive endpoint or business invariant is introduced, its tests must be added in the same change. A green test count alone is insufficient if a new critical path has no regression test.

## Evidence and maintenance

Every hardening phase should add or update phase-specific tests and documentation. Test names should describe the security or business invariant being proved. Temporary test bypasses, skipped security checks, ignored failures, and assertions that merely mirror implementation without checking behavior are prohibited.

Phase 30 is considered complete only after the implemented test strategy is present, the critical test inventory is enforced by automated checks, and the final `main` commit has a successful GitHub Actions verification run.
