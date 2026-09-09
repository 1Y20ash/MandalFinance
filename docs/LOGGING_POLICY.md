# MandalFinance Application Logging Policy

## Purpose

MandalFinance application logs provide operational visibility for availability, failures, latency and request tracing. They are distinct from the database-backed audit trail used for financial and accountability events.

## Logging rules

- Application logs are emitted as structured JSON to standard output so deployment platforms can collect them without requiring local files.
- Each request receives an `X-Request-ID` correlation identifier. A supplied identifier is preserved so a request can be traced across trusted infrastructure.
- Request telemetry records only HTTP method, URL path, status and duration. Query strings, request bodies, cookies and authorization headers are not logged.
- Credential-like values such as passwords, tokens, API keys, secrets and authorization material are redacted by a logging filter if accidentally included in a log message or structured field.
- Production log level is controlled by `LOG_LEVEL` and defaults to `INFO`; unsupported values fall back to `INFO`.
- Application exceptions are logged with the correlation identifier while the client receives a generic 500 response.
- Logs must not be used as a secondary data store for personal data, financial documents, credentials, payment secrets or full request payloads.

## Retention and access

Log retention is controlled by the production hosting/log aggregation platform. Access must be restricted to personnel who require operational or security visibility. The platform retention period must be configured to the minimum period necessary for incident response, reliability and security monitoring and documented in the production deployment record.

## Relationship to audit logging

Business events such as financial mutations, approvals, payments and document actions belong in the immutable/auditable database history described by the Audit Logging Policy. Operational request logs must not be treated as the authoritative financial history.

## Verification

Phase 20 requires the CI suite to verify structured formatting, credential redaction and request correlation. Production verification must additionally confirm that the deployment platform receives stdout logs and that configured retention/access controls match this policy.
