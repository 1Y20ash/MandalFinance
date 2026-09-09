# Authentication Security Policy

**Phase:** 9 — Authentication Hardening  
**Status:** Implemented pending CI verification

## Scope

This policy defines authentication controls for MandalFinance member accounts and administrative access.

## Controls

- Passwords are never stored in plaintext. New passwords use PBKDF2-HMAC-SHA256 with 600,000 iterations and a unique 32-byte random salt.
- Login attempts are rate-limited to 5 POST attempts per minute per normalized IP/account key, using shared persistent rate-limit storage in production.
- Login failures use a generic `Invalid username or password.` response so valid usernames cannot be distinguished from unknown accounts or accounts that are pending/deactivated.
- Registration duplicate-account responses are also generic and do not disclose whether a username or email already exists.
- Successful authentication creates a fresh Flask-Login session.
- Flask-Login strong session protection is enabled to invalidate sessions when an unexpected client identity change is detected.
- Session and remember-me cookies are HttpOnly and SameSite=Lax; Secure is enabled in production.
- Logout is POST-based and CSRF-protected; the existing GET logout endpoint only renders a CSRF-protected POST form.
- Authenticated users can change their password only after supplying the current password. A successful change invalidates the current login session and requires a new sign-in.
- Password-change events and failed attempts are audit logged without recording passwords or authentication secrets.
- Protected application functions continue to require authentication and applicable RBAC permissions server-side.

## Password reset

Self-service password reset by email is intentionally not enabled until a verified outbound mail provider and reset-token lifecycle are implemented. The application must not expose password-reset tokens through pages, logs, audit records, or client-visible responses.

## Verification requirements

Authentication changes must be covered by automated tests for generic failures, rate limiting, session protection, cookie configuration, password-change authorization, old-password invalidation, CSRF, and audit behavior before release.
