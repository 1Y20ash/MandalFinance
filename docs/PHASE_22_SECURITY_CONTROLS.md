# Phase 22 — Application Security Controls

## Scope

This phase hardens the application against the attack classes identified in the production-readiness plan.

## Controls

- **CSRF:** Flask-WTF CSRF protection is initialized globally; state-changing routes use POST and existing forms are covered by CSRF tokens.
- **XSS:** Flask/Jinja templates use escaped rendering by default. User-controlled values are not rendered through dynamically constructed templates. The logout page was moved from `render_template_string` to a normal template.
- **SQL injection:** Database access uses SQLAlchemy query expressions and bound parameters rather than string-built SQL for user input.
- **Command injection:** No application request path invokes a shell or subprocess with user-controlled input.
- **Template injection:** Runtime template source is not built from request data; authentication logout rendering uses a static template.
- **Path traversal:** Storage paths reject absolute paths, drive-qualified paths, empty/dot/dot-dot components, and backslash traversal. Local storage also verifies the resolved path remains below the configured upload directory.
- **SSRF:** Remote storage access is derived from trusted server configuration (`SUPABASE_URL`), not from request-controlled URLs. Application uploads and entity identifiers cannot select an arbitrary remote destination.
- **Open redirects:** Authentication `next` targets are accepted only when they are application-relative paths with no scheme or network location.
- **Unsafe uploads:** Uploads are size-limited, extension/MIME checked, sanitized, and signature checked for supported binary formats. Production storage is private Supabase object storage.
- **IDOR/BOLA:** Resource routes require authenticated users plus explicit permission checks. Financial records are intentionally organization-wide resources for authorized roles rather than user-owned objects.
- **Session attacks:** Secure production cookies, HttpOnly cookies, SameSite=Lax, CSRF protection, and POST-based logout reduce session abuse and cross-site state changes.
- **Brute force:** Login POSTs are rate-limited per remote address and normalized account identifier.
- **Credential enumeration:** Login failures intentionally return the same generic invalid-credential message regardless of whether the identifier exists. Registration approval remains an explicit workflow and is not an authentication oracle.

## Verification

The Phase 22 security regression suite covers local redirect validation, traversal rejection, filename sanitization, MIME/extension validation, and file-signature validation. Existing authentication, authorization, CSRF, upload, and rate-limit tests remain part of the full CI security suite.

Phase completion requires the GitHub Actions security workflow to pass on the exact final `main` commit after all changes are applied.
