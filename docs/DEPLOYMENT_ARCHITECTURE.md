# MandalFinance Deployment Architecture

**PDP Phase:** 33 — Deployment Architecture  
**Status:** Controlled architecture baseline

## 1. Architecture boundary

MandalFinance is a server-rendered Flask application with a single application factory and a production entrypoint in `server.py`.

The deployment boundary is intentionally simple:

```text
Browser
  |
  | HTTPS
  v
Vercel / production hosting
  |
  | WSGI application entrypoint
  v
server.py
  |
  v
Flask application factory (`app.create_app`)
  |
  +--> Route blueprints
  +--> Service layer / business guards
  +--> SQLAlchemy + Flask-Migrate
  +--> Flask-Login / CSRF / rate limiting
  +--> Supabase private object storage
  +--> Razorpay payment gateway
  +--> Shared Redis rate-limit storage
  |
  v
Managed PostgreSQL
```

The diagram describes application responsibilities, not a guarantee that every component is hosted by the same provider.

## 2. Application entrypoint

`server.py` is the canonical production application entrypoint. It creates the Flask application through `create_app()` and does not create database tables directly from SQLAlchemy metadata.

Database schema management is owned by Flask-Migrate/Alembic. Production deployment must run the controlled migration process rather than relying on application startup to mutate the schema.

The development-only migration behavior in `server.py` is guarded by the development environment and is not the production deployment mechanism.

## 3. Hosting boundary

The repository's Vercel configuration exposes `server.py` as the Python function entrypoint and explicitly includes the server-rendered templates required by the application.

The hosting layer is responsible for HTTPS ingress, request execution, and deployment packaging. It must not become the system of record for financial data, documents, audit history, or rate-limit state.

Production configuration and secrets are supplied by the hosting environment. Secrets must never be committed to the repository or embedded in frontend templates.

## 4. Stateful systems

The following state must remain outside ephemeral application execution:

- PostgreSQL — authoritative application and financial data.
- Supabase private storage — protected uploaded documents/object data.
- Shared Redis — production rate-limit state.

Local process memory, local SQLite files, application instance memory, and ephemeral deployment files must not be used as production system-of-record storage.

## 5. Financial and payment boundaries

Financial records are persisted in PostgreSQL and derived from the authoritative ledger model. Razorpay is the production payment provider. Payment verification and webhook processing remain server-side.

A deployment must not move payment verification, ledger mutation, authorization, or document authorization into browser-only logic.

## 6. Security boundaries

Production deployment requires:

- HTTPS.
- Production configuration validation.
- Secure session cookies.
- CSRF protection for applicable state-changing browser requests.
- Persistent shared Redis rate limiting.
- Private Supabase storage.
- Razorpay production configuration.
- Redacted operational logging.
- Immutable/tamper-evident audit logging.
- Security response headers.
- Generic external error responses.

## 7. Deployment sequence

Deployment is deliberately separated from database and application verification:

1. Build from a clean repository revision.
2. Install the pinned/controlled dependency environment used by CI.
3. Validate production configuration without exposing secrets.
4. Verify migration heads.
5. Apply migrations using the controlled deployment procedure.
6. Start the application through `server.py`.
7. Verify liveness/readiness and critical production smoke paths.
8. Confirm external processor/storage dependencies are configured correctly.

No deployment should be used as a substitute for CI, migration verification, security tests, or the later production smoke test owned by PDP Phase 39.

## 8. Failure boundaries

If PostgreSQL, private storage, Redis, or required payment configuration is unavailable or invalid, production configuration validation must fail closed rather than silently substituting SQLite, memory storage, mock payments, or public document storage.

Health endpoints may report dependency degradation, but they must not expose raw exception details, credentials, connection strings, or internal infrastructure information.

## 9. Deployment anti-patterns prohibited by this baseline

- Running the Flask development server as the production architecture.
- Using SQLite in production.
- Using process-local memory for production rate limiting.
- Storing uploaded private documents on ephemeral local disk as the system of record.
- Running database schema creation through `db.create_all()` in production.
- Performing payment verification in browser JavaScript only.
- Exposing Supabase service-role credentials to the browser.
- Committing production secrets.
- Treating a successful deployment-provider status as proof that security, migrations, or financial regression tests passed.

## 10. Evidence boundary

This phase establishes the repository architecture and deployment contract. It does **not** claim that an actual production deployment is healthy.

Actual production values, provider regions, external connectivity, deployment smoke tests, and post-deployment verification remain environment-specific evidence for the later PDP phases.
