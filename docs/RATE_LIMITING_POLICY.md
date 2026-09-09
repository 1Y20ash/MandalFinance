# MandalFinance Rate Limiting Policy

**PDP phase:** 23 — Rate Limiting  
**Scope:** Authentication, financial operations, documents, payments, administration and abuse-sensitive public operations

## Objective

MandalFinance uses server-side rate limiting as a defense against brute-force attacks, automated abuse, resource exhaustion and accidental request storms. Rate limiting is defense-in-depth; it does not replace authentication, authorization, CSRF protection or payment verification.

## Storage requirement

Production rate-limit state **must** use shared persistent storage. `memory://` is permitted only for development/testing and must never be accepted by production configuration.

Configure either:

- `RATELIMIT_STORAGE_URI` — preferred explicit Flask-Limiter storage URI; or
- `REDIS_URL` — supported deployment-platform Redis connection variable.

The production configuration rejects startup when neither is configured and readiness reports rate-limit storage as a required production dependency.

## Application-wide protection

A conservative default ceiling of **300 requests per minute per remote address** applies to routes without a tighter endpoint-specific policy. Health probes are explicitly exempt so infrastructure monitoring cannot be blocked by normal application traffic.

## Sensitive endpoint policies

| Operation | Limit | Keying / scope |
|---|---:|---|
| Login | 5/minute | IP + normalized account identifier |
| Registration | 5/hour | Remote address |
| Public donation initiation | 10/hour | Remote address |
| Online payment confirmation | 20/minute | Remote address |
| Offline donation creation | 20/minute | Remote address |
| Income creation | 20/minute | Remote address |
| Expense creation | 20/minute | Remote address |
| Expense payment/approval/rejection | 20–30/minute | Remote address |
| Contribution creation/payment | 20/minute | Remote address |
| Document upload/replacement | 20/minute | Remote address |
| Document download/integrity verification | 30/minute | Remote address |
| Evidence-pack generation | 5/minute | Remote address |
| Administrative reads | 60/minute | Remote address |
| Administrative writes | 30/minute | Remote address |

Password-reset and privacy-request endpoints are not currently exposed by the application. If introduced, they must receive dedicated limits before release.

Razorpay webhook delivery is not given an aggressive endpoint-specific limit because provider retries must remain reliable. Its signature and event validation remain mandatory; the global ceiling is the final abuse guard.

## 429 behavior

A rate-limited request returns HTTP `429 Too Many Requests`. The application provides a generic user-facing page that:

- does not expose implementation details;
- does not reveal account existence or internal identifiers;
- tells the user to wait and retry;
- provides a safe navigation option;
- works with the existing MandalFinance responsive UI.

Flask-Limiter response headers are enabled so clients and operators can respect the applicable retry window.

## Privacy and security requirements

Rate-limit keys must not contain passwords, tokens, payment credentials or other unnecessary personal data. Authentication uses the remote address plus a normalized username solely to prevent a single account from being brute-forced through repeated attempts while avoiding storage of the supplied password.

Rate-limit failures are handled before the protected operation executes, preventing an abusive request from reaching the business logic.

## Verification

Phase 23 is complete only when the repository test suite demonstrates:

1. registration throttling produces a 429 after the configured threshold;
2. public payment/donation initiation is throttled;
3. the 429 response is user-safe;
4. retry metadata is present;
5. health probes remain available;
6. production configuration rejects missing shared storage;
7. production configuration rejects `memory://` storage;
8. valid Redis/shared storage configuration is accepted;
9. existing authentication, financial, document and security tests continue to pass;
10. CI passes on the exact final `main` commit.

A rate-limit implementation is not considered complete merely because the decorator exists in source code.
