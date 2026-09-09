# MandalFinance Error Handling Policy

## Purpose

Phase 28 establishes a consistent, privacy-safe error boundary for MandalFinance. Errors must help the user recover without exposing credentials, database details, filesystem paths, stack traces, framework internals, payment-provider secrets, document metadata, or other implementation details.

This document is an engineering control and is not a legal or security certification.

## Error classes

### Expected HTTP errors

Expected client/request failures such as 400, 401, 403, 404, 405, 408, 413, 415, 422, and 429 receive controlled responses. Browser requests receive a user-friendly HTML error page; explicit JSON/API-style requests receive a stable JSON error contract.

The response contains only a safe status code and generic message. The original exception description is not copied into the client response.

### Unexpected application errors

Unhandled exceptions are caught at the application boundary. The server logs the exception through the existing structured logging pipeline, and the client receives only a generic 500 response. The exception object, traceback, SQL statement, connection string, filesystem path, request body, cookies, and credentials are never rendered to the client.

The database session is rolled back before returning the 500 response so a failed request cannot leave the current unit of work pending in the session.

### Rate-limit errors

429 responses retain the existing privacy-safe rate-limit page and JSON contract. Detailed limiter internals and key material are not disclosed.

## Response contract

JSON error responses use this shape:

```json
{
  "error": {
    "code": 404,
    "message": "The requested page could not be found."
  }
}
```

Messages are deliberately generic and selected by server-controlled status code.

## Health endpoints

Health/readiness endpoints may expose dependency status such as `HEALTHY`, `UNHEALTHY`, `ok`, or `failed`, but must not expose raw database exception strings, connection URLs, credentials, SQL, stack traces, or infrastructure paths. Detailed diagnostics remain server-side in privacy-safe logs.

## Logging boundary

Unexpected errors are recorded using the Phase 19 structured logging controls. The logging policy remains authoritative for request correlation, credential-like redaction, and exclusion of request bodies, query strings, cookies, and authentication headers.

## Development versus production

Debug tracebacks must never be enabled as a production response mechanism. Production configuration must continue to use safe client responses and server-side diagnostics only. Development debugging may be used locally, but production behavior is covered by automated regression tests.

## Required regression coverage

Phase 28 tests verify:

- generic HTML handling for missing routes;
- explicit JSON handling for missing routes;
- generic 500 handling for unexpected exceptions;
- absence of injected exception secrets from client responses;
- server-side logging of unexpected failures;
- safe JSON 500 contract;
- health-endpoint suppression of raw database exception details.

## Engineering rule

**Never turn an exception message into user-visible output merely because it is convenient for debugging.** Add a server-side diagnostic with correlation context instead, then return the smallest useful client-safe response.
