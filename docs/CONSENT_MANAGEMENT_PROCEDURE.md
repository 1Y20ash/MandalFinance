# Consent Management Procedure

## Scope

MandalFinance uses consent only for processing that actually depends on consent. Core account, financial accounting, security and legally required processing must not be represented as optional consent merely to obtain agreement.

## Optional purposes

The application currently supports two separately controlled optional purposes:

- **Analytics:** optional analytics used to understand aggregate service usage.
- **Communications:** optional non-essential service communications that are not required to operate the account.

Each purpose is presented independently. Granting one purpose does not grant the other or authorize core processing.

## Required evidence

Each consent record contains the authenticated user, purpose, status, notice version, source and timestamps. The application records the decision against the Privacy Notice version presented at the time of the decision.

## Grant rules

1. Consent must be affirmative and purpose-specific.
2. Optional consent is never pre-selected.
3. The UI requires an explicit confirmation control for each grant action.
4. The grant action is separate for every optional purpose.
5. Core processing is not conditional on granting optional consent.
6. Missing or invalid purpose values are rejected server-side.
7. Consent is accepted only for an authenticated user and a purpose explicitly allow-listed by the application.
8. The server, not the browser, is authoritative for the consent status and purpose.
9. The notice version and source are recorded with the decision.

## Withdrawal rules

1. Withdrawal is available from the same Privacy Center without requiring a new grant.
2. Withdrawal is a one-step action and is not made harder than granting consent.
3. Withdrawal changes the current status to `WITHDRAWN` and records the withdrawal timestamp.
4. Applications using optional processing must check the current status before performing that processing.
5. Withdrawal does not retroactively invalidate processing that was lawful before withdrawal.

## Auditability

Consent changes are recorded in the audit log with the purpose, previous status, resulting status, notice version and source. Audit entries avoid unnecessary personal data.

## Versioning

A consent decision is tied to `NOTICE_VERSION`. When the applicable notice version changes, a new consent decision must be obtained for processing that depends on the changed notice or purpose. The application must not silently treat an old decision as consent to a materially changed purpose.

## Review

Consent purposes, wording, UI controls, downstream enforcement and the notice version must be reviewed whenever optional processing changes. Regression tests must cover explicit grant, rejection without confirmation, purpose validation, withdrawal, version recording and separation from core processing.
