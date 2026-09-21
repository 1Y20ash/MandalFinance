# MandalFinance

A secure, server-rendered financial management platform for mandal/community organizations. MandalFinance centralizes donations, income, expenses, budgets, contributions, vendors, documents, reconciliation, audit history, public transparency, and online payments while enforcing financial-integrity, authorization, privacy, and security controls at the application boundary.

> **Engineering note:** This README documents the repository and its implemented architecture. It is not a legal, accounting, statutory-compliance, penetration-test, or financial-audit certification.

## Table of Contents

- [Overview](#overview)
- [Core Capabilities](#core-capabilities)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Financial Integrity Model](#financial-integrity-model)
- [Authentication and Authorization](#authentication-and-authorization)
- [Payments and Donations](#payments-and-donations)
- [Document Security](#document-security)
- [Audit Logging and Privacy](#audit-logging-and-privacy)
- [PWA and Frontend](#pwa-and-frontend)
- [Database and Migrations](#database-and-migrations)
- [Local Development](#local-development)
- [Environment Configuration](#environment-configuration)
- [Testing](#testing)
- [Production Deployment](#production-deployment)
- [Security Practices](#security-practices)
- [Operational Documentation](#operational-documentation)
- [Contributing](#contributing)
- [License](#license)

## Overview

MandalFinance is designed for organizations that need a controlled digital system for managing community finances. The application uses Flask on the server side, SQLAlchemy/Flask-Migrate for persistence, PostgreSQL for production financial data, private object storage for protected documents, Redis for production rate-limit state, and Razorpay for online payment processing.

The design intentionally keeps security-sensitive decisions on the server. Browser code is treated as an interface rather than an authority for:

- financial authorization;
- payment verification;
- ledger mutation;
- document authorization;
- audit-history integrity; or
- access-control decisions.

### Main financial workflow

```text
User / Administrator
        |
        v
Authentication + RBAC
        |
        v
Authorized Financial Action
        |
        +----------------------+
        |                      |
        v                      v
Financial Service       Validation / Guards
        |                      |
        +----------+-----------+
                   |
                   v
             PostgreSQL
                   |
          +--------+--------+
          |                 |
          v                 v
     Ledger / Records   Audit Evidence
```

For online donations:

```text
Public Donor
    |
    v
Donation Checkout
    |
    v
Payment Gateway
    |
    v
Server-side Verification
    |
    v
Donation / Income Recording
    |
    v
Receipt Generation
    |
    v
Audit / Financial Records
```

## Core Capabilities

### Financial management

- Donation recording and receipt generation.
- Online donation checkout and payment verification.
- Income and income-category management.
- Expense recording and expense-category management.
- Contributions and contribution payments.
- Vendor management.
- Budget creation and management.
- Account balances and financial controls.
- Ledger posting and reconciliation.
- Financial-event tracking.

### Administration

- User registration and approval workflows.
- Authentication and session management.
- Role-based access control (RBAC).
- Administrative user and role management.
- Audit-log review.
- Financial-event review.
- Controlled financial actions and approval boundaries.

### Documents

- Protected document upload.
- File validation and metadata handling.
- Private object-storage integration.
- Authorized document viewing/download.
- Integrity and replacement/version controls.

### Public-facing features

- Public donation experience.
- Public contact, terms, refund, privacy, and transparency pages.
- Aggregate-oriented transparency information.
- Secure online payment integration.

### Platform/security features

- CSRF protection.
- Authentication and object-level authorization.
- Server-side payment verification.
- Webhook signature verification.
- Persistent Redis-backed rate limiting in production.
- Security response headers and CSP.
- Privacy-safe error handling.
- Tamper-evident/immutable audit controls.
- Production configuration validation.
- Health/readiness endpoints.
- PWA support with install assets and service worker.

## Architecture

MandalFinance is a server-rendered Flask application with a single application factory.

```text
Browser
  |
  | HTTPS
  v
Vercel / Production Hosting
  |
  v
server.py
  |
  v
app.create_app()
  |
  +--> Flask route blueprints
  |
  +--> Service layer
  |      +--> Donations
  |      +--> Income
  |      +--> Expenses
  |      +--> Contributions
  |      +--> Documents
  |      +--> Ledger
  |      +--> Reconciliation
  |      +--> Financial controls
  |
  +--> Security boundaries
  |      +--> Flask-Login
  |      +--> CSRF
  |      +--> RBAC
  |      +--> Rate limiting
  |      +--> Financial guards
  |
  +--> Persistence
  |      +--> SQLAlchemy
  |      +--> Flask-Migrate / Alembic
  |      +--> PostgreSQL
  |
  +--> External services
         +--> Razorpay
         +--> Supabase private storage
         +--> Shared Redis
```

The production deployment architecture deliberately keeps PostgreSQL, private document storage, and rate-limit state outside ephemeral application execution.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| ORM | SQLAlchemy / Flask-SQLAlchemy |
| Database migrations | Flask-Migrate / Alembic |
| Production database | PostgreSQL |
| Authentication | Flask-Login |
| Request protection | Flask-WTF / CSRF |
| Rate limiting | Flask-Limiter + Redis |
| Payments | Razorpay |
| Private storage | Supabase Storage |
| PDF generation | ReportLab / fpdf2 / pypdf |
| Frontend | Server-rendered HTML, CSS, JavaScript |
| Hosting | Vercel |
| Testing | pytest |
| CI | GitHub Actions |
| PWA | Web App Manifest + Service Worker |

## Project Structure

```text
MandalFinance/
├── app/
│   ├── models/                 # Database models and financial entities
│   ├── routes/                 # Flask route blueprints
│   ├── services/               # Business logic and security boundaries
│   ├── utils/                  # Shared security, PDF, storage and helper code
│   ├── templates/              # Server-rendered HTML templates
│   ├── static/
│   │   ├── css/                # Application stylesheets
│   │   ├── img/                # Logos, PWA icons and splash assets
│   │   ├── js/                 # Frontend JavaScript
│   │   ├── manifest.json       # PWA manifest
│   │   └── sw.js               # Service worker
│   ├── assets/                 # Bundled application assets
│   └── __init__.py             # Flask application factory
│
├── migrations/
│   ├── versions/               # Alembic migration history
│   └── env.py
│
├── scripts/
│   ├── seed_data.py
│   └── verify_production_config.py
│
├── tests/                      # Security, financial and integration tests
├── docs/                       # Engineering and security policies
├── server.py                   # Production application entrypoint
├── vercel.json                 # Vercel deployment configuration
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Python/Vercel configuration
├── pytest.ini                  # pytest configuration
└── .env.example                # Environment-variable template
```

## Financial Integrity Model

Financial data is treated as a controlled domain rather than ordinary CRUD data.

Important principles include:

1. **Server-side authority** — financial mutations are validated by backend services and guards.
2. **Decimal-safe money handling** — monetary values use database/application types appropriate for financial arithmetic rather than binary floating-point calculations.
3. **Ledger integrity** — authoritative financial records and ledger relationships are protected by business rules.
4. **Authorization before mutation** — authenticated identity alone does not grant permission to perform every financial action.
5. **Approval controls** — sensitive financial workflows include authorization and approval boundaries where required.
6. **Reconciliation** — financial records can be reconciled and checked against accounting invariants.
7. **Auditability** — important financial events are recorded for traceability.
8. **Immutability controls** — finalized/locked historical records are protected against unauthorized mutation.
9. **Fail-closed behavior** — unsafe production configuration must not silently fall back to development mechanisms.

A successful deployment-provider build is therefore not considered sufficient evidence of financial correctness. The automated security/financial-integrity gate and production verification remain separate release requirements.

## Authentication and Authorization

The application uses Flask-Login for session authentication and a dedicated RBAC/security layer for authorization.

Security boundaries include:

- authenticated-session enforcement;
- registration approval where applicable;
- role-based permissions;
- object-level access checks;
- financial authorization guards;
- CSRF protection on applicable state-changing browser requests;
- login and sensitive-endpoint rate limiting;
- safe redirect validation;
- generic authentication and authorization failures.

Authorization is enforced server-side. Frontend visibility of a button or page is never treated as proof that an operation is authorized.

## Payments and Donations

Online donations use Razorpay as the production payment gateway.

The payment design keeps sensitive operations on the server:

1. Create/prepare the donation/payment flow.
2. Validate the requested donation details.
3. Create or process the gateway-side payment order through the backend.
4. Verify returned payment information server-side.
5. Validate payment signatures.
6. Protect against duplicate/idempotent confirmation.
7. Record the donation and corresponding financial information.
8. Generate the receipt from the controlled receipt design.
9. Preserve audit evidence.

Webhook processing is separately protected with signature verification and duplicate-safe handling.

### Receipt generation

The receipt workflow is designed around the supplied receipt artwork rather than replacing it with an unrelated generated design. Dynamic fields are overlaid onto the existing receipt layout, including:

- donor name;
- amount in words;
- numeric ₹ amount;
- relevant donation/receipt details.

Receipt generation is part of the successful donation-recording flow and should not be treated as a replacement for the authoritative financial record.

## Document Security

Documents may contain sensitive financial or organizational information and are therefore handled as private data.

Production architecture uses:

- private object storage;
- server-side authorization;
- file-type/content validation;
- controlled upload limits;
- protected download/view operations;
- integrity/version controls;
- non-public storage policies.

The local filesystem must not be treated as the production system of record for private documents because Vercel/serverless execution is ephemeral.

## Audit Logging and Privacy

MandalFinance separates operational logging from financial audit evidence.

### Operational logging

Operational logs should help diagnose failures without exposing:

- passwords;
- authentication/session secrets;
- payment secrets;
- storage service-role credentials;
- raw private documents;
- unnecessary donor information.

### Audit evidence

Financially significant events are recorded through the audit/financial-event mechanisms so that authorized administrators can trace important actions.

The repository also includes explicit policies for:

- audit logging;
- data breach response;
- dependency security;
- error handling;
- frontend privacy;
- public transparency;
- third-party processors;
- DPDP engineering controls.

## PWA and Frontend

MandalFinance includes Progressive Web App support.

Relevant files include:

- `app/static/manifest.json`
- `app/static/sw.js`
- `app/static/js/pwa-install.js`
- `app/static/css/pwa-install.css`
- `app/static/img/icon-192.svg`
- `app/static/img/icon-512.svg`
- `app/static/img/pwa-splash-192.svg`
- `app/static/img/pwa-splash-512.svg`

The app icon assets are kept separate from the dedicated splash/loading artwork. This prevents a loading-screen presentation change from unintentionally changing the installed application icon.

## Database and Migrations

MandalFinance uses SQLAlchemy models with Flask-Migrate/Alembic.

Migration files are stored under:

```text
migrations/versions/
```

Production schema changes must go through migrations. The application must not use `db.create_all()` as a production schema-management mechanism.

### Migration principles

- Keep migration revisions within Alembic's identifier constraints.
- Preserve the correct migration dependency chain.
- Make migrations safe to apply against the intended baseline.
- Check for existing objects when required by the deployment baseline.
- Avoid destructive downgrades for protected financial data.
- Verify migration heads in CI.
- Reconstruct a clean PostgreSQL database during the release gate.

## Local Development

### 1. Clone the repository

```bash
git clone https://github.com/1Y20ash/MandalFinance.git
cd MandalFinance
```

### 2. Create a virtual environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

On Windows, copy the file using the equivalent PowerShell command:

```powershell
Copy-Item .env.example .env
```

Use development-only values locally. Never copy production secrets into a committed file.

### 5. Initialize the development database

The development server can run the controlled migration process through Flask-Migrate when `FLASK_ENV=development`.

You can also run migrations explicitly:

```bash
flask db upgrade
```

### 6. Start the application

```bash
python server.py
```

The default development server listens on:

```text
http://127.0.0.1:5000
```

## Environment Configuration

The complete variable template is maintained in [`.env.example`](.env.example).

Important configuration groups include:

### Application

- `FLASK_APP`
- `FLASK_ENV`
- `SECRET_KEY`
- `LOG_LEVEL`

### Database

- `DATABASE_URL`

Development may use SQLite. Production must use PostgreSQL.

### Private document storage

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_STORAGE_BUCKET`
- `SUPABASE_STORAGE_PRIVATE`

The service-role key must remain server-side.

### Payment gateway

- `PAYMENT_GATEWAY_DRIVER`
- `ONLINE_DONATION_ACCOUNT_ID`
- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET`

Development can use the mock gateway where supported. Production must use the configured Razorpay integration.

### Rate limiting

- `RATELIMIT_STORAGE_URI`
- `REDIS_PROVIDER_NAME`

Production requires persistent shared Redis-backed rate-limit storage. Memory-only rate limiting is not an acceptable production configuration.

### Upload limits

- `UPLOAD_FOLDER`
- `MAX_CONTENT_LENGTH`
- `MAX_DOCUMENT_SIZE`

### Secrets

Never commit:

- production database credentials;
- payment secrets;
- webhook secrets;
- Supabase service-role keys;
- Redis credentials;
- Flask production secret keys.

## Testing

Run the complete test suite with:

```bash
pytest
```

The test suite covers security, financial integrity, authentication, authorization, payments, documents, privacy, migrations, logging, rate limiting, health checks, and critical application flows.

### Important test areas

```text
tests/
├── test_auth.py
├── test_rbac.py
├── test_donations.py
├── test_online_donation_flow.py
├── test_payment_gateway.py
├── test_documents.py
├── test_document_security.py
├── test_receipts.py
├── test_income.py
├── test_expenses.py
├── test_contributions.py
├── test_ledger.py
├── test_ledger_reconciliation.py
├── test_audit_logging.py
├── test_security_headers.py
├── test_rate_limiting.py
├── test_pdp_hardening.py
├── test_phase22_security_controls.py
├── test_phase24_processors.py
├── test_phase25_breach_response.py
├── test_phase26_public_transparency.py
├── test_phase27_frontend_privacy.py
├── test_phase28_error_handling.py
├── test_phase29_dependency_audit.py
├── test_phase30_testing.py
├── test_phase32_production_configuration.py
├── test_phase33_deployment_architecture.py
├── test_phase34_health_checks.py
├── test_phase35_dpdp_compliance_matrix.py
├── test_phase36_final_security_review.py
├── test_phase37_release_gate.py
├── test_phase38_single_clean_deployment.py
└── test_phase39_financial_events.py
```

### CI release gate

The repository's GitHub Actions workflow:

```text
.github/workflows/security-financial-integrity.yml
```

is the required automated gate.

The release process is intended to verify, at minimum:

1. dependency installation;
2. dependency security scanning;
3. Python source compilation;
4. production configuration preflight;
5. migration verification;
6. clean PostgreSQL migration;
7. complete pytest regression/security suite.

A failed security, migration, financial-integrity, or regression stage blocks release progression.

## Production Deployment

Vercel is configured as the production hosting layer.

The relevant configuration is:

```text
vercel.json
```

The application entrypoint is:

```text
app/server.py
```

which creates the Flask application using:

```python
from app import create_app
```

### Production deployment principles

1. Deploy from a clean, reviewed `main` revision.
2. Pass the complete CI security/financial-integrity gate.
3. Validate production configuration.
4. Verify migration state.
5. Apply controlled migrations.
6. Build and deploy the application.
7. Verify health/readiness endpoints.
8. Run production smoke checks for critical flows.
9. Confirm external dependencies are correctly configured.

Vercel is not treated as the source of truth for financial data, private documents, audit history, or persistent rate-limit state.

### Vercel configuration

The repository's `vercel.json`:

- uses `app/server.py` as the Python function;
- includes server-rendered templates in the deployment bundle;
- includes the receipt PDF asset;
- runs database migrations for production deployments through the configured build command.

## Security Practices

MandalFinance follows a defense-in-depth approach.

### Application security

- CSRF protection.
- Authentication and authorization.
- Object-level access controls.
- Server-side financial guards.
- Rate limiting.
- Safe redirect validation.
- Generic error responses.
- Request logging with privacy boundaries.

### Browser security

The application configures headers including:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy`
- `Permissions-Policy`
- `Content-Security-Policy`
- `Cross-Origin-Opener-Policy`
- `Cross-Origin-Resource-Policy`
- production `Strict-Transport-Security`

### Data security

- PostgreSQL for production financial state.
- Private object storage for protected documents.
- Server-side payment verification.
- Controlled audit history.
- Persistent shared Redis for production rate limiting.
- No production fallback to SQLite, mock payments, public document storage, or memory-only rate limiting.

### Fail-closed principle

Production configuration validation is intended to reject unsafe configurations rather than silently substitute development defaults.

Examples of unsafe production conditions include:

- SQLite as the production database;
- mock payment gateway;
- missing payment/webhook configuration;
- public document storage;
- missing persistent Redis rate-limit storage;
- missing required provider identity/configuration.

## Operational Documentation

The `docs/` directory contains the repository's detailed engineering policies.

| Document | Purpose |
|---|---|
| `AUDIT_LOGGING_POLICY.md` | Audit logging requirements |
| `DATA_BREACH_RESPONSE_PROCEDURE.md` | Incident/breach response procedure |
| `DEPENDENCY_SECURITY_POLICY.md` | Dependency security controls |
| `DEPLOYMENT_ARCHITECTURE.md` | Production architecture and deployment boundary |
| `DPDP_COMPLIANCE_MATRIX_POLICY.md` | DPDP engineering control mapping |
| `ERROR_HANDLING_POLICY.md` | Error-handling and information-disclosure rules |
| `FINAL_SECURITY_REVIEW.md` | Cross-cutting security review |
| `FRONTEND_PRIVACY_POLICY.md` | Browser/frontend privacy controls |
| `HEALTH_CHECK_POLICY.md` | Liveness/readiness requirements |
| `LOGGING_POLICY.md` | Operational logging policy |
| `PDP_COMPLIANCE_MATRIX.md` | Phase/control traceability |
| `PHASE_22_SECURITY_CONTROLS.md` | Security-control implementation baseline |
| `PRODUCTION_CONFIGURATION_TEST_POLICY.md` | Production configuration testing |
| `PUBLIC_TRANSPARENCY_POLICY.md` | Public transparency boundaries |
| `RATE_LIMITING_POLICY.md` | Rate-limit policy |
| `RELEASE_GATE_POLICY.md` | Release-gate requirements |
| `SECURITY_HEADERS_POLICY.md` | Browser security headers |
| `SINGLE_CLEAN_DEPLOYMENT_POLICY.md` | Clean deployment requirements |
| `TESTING_STRATEGY.md` | Automated testing strategy |
| `THIRD_PARTY_PROCESSOR_REGISTER.md` | External processor controls |

These documents are intentionally more detailed than the README and should be consulted when changing security-sensitive behavior.

## Contributing

When modifying MandalFinance:

1. Understand the affected financial/security boundary before changing code.
2. Keep business logic in the appropriate service layer rather than duplicating it in routes.
3. Add or update regression tests for new sensitive behavior.
4. Preserve authorization, audit, privacy, and financial-integrity controls.
5. Use Alembic migrations for schema changes.
6. Never commit secrets or production credentials.
7. Run the relevant tests locally.
8. Ensure the final `main` revision passes the complete CI gate.
9. Verify production behavior for changes affecting deployment, payments, documents, migrations, or other critical flows.

### Changes involving money movement

Any change involving donations, payments, income, expenses, contributions, ledger posting, reconciliation, balances, or financial approval rules should be treated as a high-risk change and accompanied by explicit regression coverage.

### Changes involving security

Any change involving authentication, authorization, storage, payment verification, webhooks, rate limiting, CSP/security headers, document access, logging, or privacy should include negative-path testing.

## License

No explicit open-source license is currently declared in the repository. Unless and until a license is added, the repository should not be assumed to grant broad rights to copy, modify, redistribute, or commercially use the code.

## Project Status

MandalFinance is under active development with an emphasis on secure financial workflows, controlled production deployment, and automated security/financial-integrity regression testing.

The authoritative implementation is the code and migration history in the repository; this README is a structured guide to that implementation and should be updated when the architecture or supported workflows materially change.
