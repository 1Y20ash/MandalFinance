# Security Headers Policy

## Purpose

MandalFinance uses browser security headers as a defense-in-depth control against framing attacks, MIME confusion, unintended referrer disclosure, unnecessary browser capabilities, cross-origin isolation issues, and script/resource injection.

## Enforced headers

Every application response receives:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Content-Security-Policy` with same-origin defaults, no plugins/objects, same-origin framing restriction, self-only form actions, restricted scripts/styles/fonts/images/connections, and `upgrade-insecure-requests`
- `Cross-Origin-Opener-Policy: same-origin`
- `Cross-Origin-Resource-Policy: same-origin`

Production responses additionally receive:

- `Strict-Transport-Security: max-age=31536000; includeSubDomains`

HSTS is intentionally production-only because enabling it during local development can force a browser to use HTTPS for the development host.

## CSP compatibility

The current server-rendered interface contains inline JavaScript and inline style attributes/blocks and loads Bootstrap from jsDelivr plus Google Fonts and Font Awesome from their established CDNs. The CSP therefore explicitly permits those existing dependencies. `object-src 'none'`, `base-uri 'self'`, `frame-ancestors 'none'`, and `form-action 'self'` remain restrictive regardless of those compatibility allowances.

A future CSP hardening pass should migrate remaining inline JavaScript/style usage to nonce- or hash-based controls and remove `'unsafe-inline'` without weakening the other directives.

## Verification

`tests/test_security_headers.py` verifies the enforced response headers and exercises the production HSTS branch. The security and financial integrity GitHub Actions workflow must pass on the exact release commit before Phase 23 can be considered complete.
