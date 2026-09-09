# Public Transparency Policy

**Status:** Controlled engineering policy  
**Applies to:** Public MandalFinance transparency pages and other unauthenticated financial disclosures  
**PDP phase:** 26 — Public Transparency

## Purpose

MandalFinance publishes enough financial information for devotees and community stakeholders to understand how the Mandal's approved finances are being managed, while preventing public disclosure of personal, authentication, payment, document, and internal-security data.

This policy is an engineering control. It does not replace the Privacy Notice, Data Principal Rights Procedure, Retention Schedule, or any applicable legal/accounting obligation.

## Publicly disclosed information

The public transparency page may disclose:

- the Mandal/event identity and public location;
- aggregate approved income;
- aggregate approved expenses;
- aggregate approved balance;
- high-level descriptions of accountability controls;
- public donation availability and generic contribution guidance.

Financial aggregates must come from the authoritative ledger summary and must represent approved/finalized financial state according to the existing ledger rules.

## Information that must never be publicly disclosed

Unauthenticated transparency responses must not expose:

- donor names, phone numbers, email addresses, or other donor identifiers;
- user account names, email addresses, password hashes, session identifiers, or roles;
- payment gateway secrets, signatures, tokens, card/bank/payment instrument data, or internal gateway payloads;
- uploaded document contents, storage paths, object keys, signed URLs, hashes tied to private records, or evidence metadata that could enable access;
- audit-log entries, request IDs, IP addresses, authentication events, or security telemetry;
- internal database IDs when they are not necessary for the public disclosure;
- unpublished budgets, approvals, vendor personal information, reconciliation details, or administrative notes;
- credentials, environment variables, service-role keys, Redis configuration secrets, or infrastructure internals.

## Disclosure boundary

The public route is intentionally aggregate-only. It must not query or serialize detailed donor, user, document, audit, or administrative records merely to render public transparency content.

Any future public financial disclosure must undergo a privacy-leakage review before implementation. If a proposed disclosure could identify an individual directly or by reasonable combination with other public information, the default is to aggregate, redact, delay, or withhold it.

## Financial integrity and accuracy

Public figures must be derived from the same authoritative financial ledger used by internal reporting. No client-supplied amount, browser state, cached form value, or duplicated module total may be used as the source of truth.

If a figure is temporarily unavailable or cannot be verified, the application must fail closed rather than publish an unverified value.

## Review and change control

Before adding a new public field, maintainers must confirm:

1. the field is necessary for a legitimate transparency purpose;
2. it is not personal or confidential information, or has been appropriately aggregated/redacted;
3. it does not expose security, payment, document, or audit data;
4. it derives from an authoritative source;
5. automated tests cover the disclosure boundary.

The policy must be reviewed whenever public routes, financial reporting, payment flows, document handling, or personal-data processing changes.

## Verification evidence

Phase 26 verification is maintained in `tests/test_phase26_public_transparency.py`. The test suite checks the controlled policy, aggregate-only template boundary, and absence of sensitive field references from the public transparency presentation.
