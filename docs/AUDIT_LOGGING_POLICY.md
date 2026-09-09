# MandalFinance Audit Logging Policy

## Purpose

The database-backed audit trail is the authoritative history for security-sensitive, financial, approval, payment, document and administrative events. It is separate from operational application logging.

## Events

Audit events should be recorded for successful and failed security actions, authentication lifecycle events, role/permission changes, financial mutations, approvals/rejections, payments, reversals/corrections, document uploads/replacements/access decisions, reconciliation actions and other privileged administrative changes.

Each event records an event identifier, actor identity where available, action, entity type/id, outcome, timestamp, request correlation identifier where available, source IP, user-agent and structured metadata.

## Integrity and immutability

- Audit rows are append-only at the application layer.
- SQLAlchemy rejects ORM updates and deletes of existing audit rows.
- PostgreSQL installations receive a database trigger that rejects `UPDATE` and `DELETE` on `audit_logs`.
- Each row contains a SHA-256 integrity digest over its immutable audit fields.
- `AuditService.verify_integrity()` can recalculate the stored digests and identify tampered rows.
- Existing audit rows are assigned stable event identifiers and integrity digests during the hardening migration.
- Business transactions may create audit entries with `commit=False` so the audit event commits atomically with the state change.

The hash is tamper-evident, not a substitute for a separately controlled database backup or external write-once log archive.

## Privacy and minimisation

Audit records must contain enough information to reconstruct accountability without becoming a secondary personal-data store. Passwords, access tokens, API keys, secrets, cookies, session material and CSRF tokens are automatically redacted from structured details. Request bodies, query strings and authentication headers are not copied into audit metadata.

IP address, user-agent and actor identity are retained only for legitimate accountability/security purposes and must follow the application's retention schedule and access controls.

## Access

Audit logs are restricted to administrators and other explicitly authorised personnel. The admin audit view is read-only and exposes integrity metadata without providing mutation controls.

## Failure handling

For security events such as failed or blocked authentication, an audit event records the failure outcome without storing the supplied password or raw credential material. Audit creation failures in a transactional business operation must prevent the corresponding transaction from being committed when the audit event is required for that operation.

## Verification

Phase 21 is complete only when the CI pipeline verifies audit creation, metadata capture, sensitive-field redaction, atomic transaction behaviour, ORM immutability, tamper detection and a clean PostgreSQL migration to the audit-hardening revision.
