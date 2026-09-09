# MandalFinance Dependency Security Policy

## Purpose

Phase 29 establishes the dependency security boundary for the Python runtime and CI environment. Dependencies are treated as supply-chain inputs because vulnerable transitive packages can compromise authentication, financial records, documents, payments, or privacy controls even when application code is otherwise correct.

This document is an engineering control, not a vulnerability-free or legal certification.

## Current manifest

The runtime/test manifest is `requirements.txt`. Direct dependencies currently include:

- Flask
- Flask-SQLAlchemy
- Flask-WTF
- Flask-Login
- Flask-Migrate
- Flask-Limiter
- redis
- psycopg2-binary
- python-dotenv
- reportlab
- fpdf2
- pytest
- werkzeug
- requests

The manifest uses minimum-version constraints rather than floating unbounded package names. CI resolves the manifest from a clean environment before running the security audit.

## Mandatory CI audit

Every push and pull request runs `pip-audit` against the dependency manifest after installation. The audit tool itself is pinned to an exact version in CI (`pip-audit==2.10.1`) so the security gate is reproducible.

The audit must fail the workflow when a known vulnerability is reported. A vulnerability may only be accepted when the dependency is removed/replaced or a documented, reviewed exception exists; silently ignoring scanner output is prohibited.

## Dependency change rules

1. Prefer actively maintained packages with security advisories and release processes.
2. Before adding a dependency, confirm that an existing package cannot safely provide the required capability.
3. Keep direct dependencies to the minimum required runtime/test set.
4. Do not add browser SDKs, analytics, tracking, payment libraries, storage clients, or other processors without completing the applicable PDP processor/privacy/security review.
5. After every dependency change, run the full regression/security suite and the dependency audit.
6. Upgrade vulnerable packages to patched versions as soon as compatibility permits.
7. Do not suppress a vulnerability merely to make CI green.
8. Record a temporary exception with package, affected version, advisory, impact, compensating control, owner, and expiry/review date when immediate remediation is technically impossible.
9. Dependency audit results must not contain application secrets or production data.
10. Production deployment must use the dependency set that passed the repository CI security gate; ad-hoc production package installation is prohibited.

## Direct versus transitive dependencies

The application manifest records direct dependencies. Framework dependencies such as Jinja2, Click, itsdangerous, MarkupSafe, SQLAlchemy, and Werkzeug may be installed transitively. `pip-audit` evaluates the resolved environment rather than relying only on the direct manifest, so transitive vulnerabilities are included in the gate.

## Unused dependency review

Dependency vulnerability scanning and unused-dependency review are separate controls. A package that is not required by the application should be removed after repository-wide usage verification and regression testing rather than being retained indefinitely. The Phase 29 audit records the manifest as the source of truth and keeps removal decisions evidence-based.

## Supply-chain limitations

A clean `pip-audit` result means no known vulnerability was reported by the configured advisory sources for the resolved environment at audit time. It does not prove that a package is free of undiscovered vulnerabilities, malicious updates, compromised maintainers, or application-level misuse.

The project therefore combines dependency scanning with pinned audit tooling, minimal direct dependencies, source-control review, CI regression testing, and the existing application security controls.

## Review cadence

Review dependencies:

- on every dependency change;
- on every security advisory affecting the stack;
- before production release;
- during the final security review;
- and when a third-party processor or browser SDK is introduced.

## Phase 29 acceptance criteria

- `requirements.txt` is the declared dependency manifest.
- CI installs from a clean environment.
- CI runs pinned `pip-audit` against the manifest.
- A known vulnerability causes CI failure.
- Dependency changes remain subject to regression/security tests.
- The PDP matrix records the evidence and any remaining dependency-maintenance work.
