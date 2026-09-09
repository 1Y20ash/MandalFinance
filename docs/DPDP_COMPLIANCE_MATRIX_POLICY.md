# Phase 35 — DPDP Compliance Matrix Governance Policy

**Status:** Engineering control established; this document does not constitute legal advice or statutory certification.

## 1. Purpose

The PDP Compliance Matrix is the authoritative engineering index for tracking the implementation state of the MandalFinance privacy, security, financial-integrity, deployment, and production-readiness controls defined by the approved PDP.

The matrix exists to prevent two failure modes:

1. claiming a control is complete when only a partial implementation exists; and
2. losing traceability between a PDP requirement, its implementation, its automated verification, its documentation, and its remaining operational evidence.

## 2. Status semantics

Each phase must use one of these states:

- **🟢 PASS** — the repository contains the required implementation/documentation evidence and automated verification appropriate to the phase, and the phase-specific CI gate has passed where one exists.
- **🟢/🟡** — meaningful implementation exists, but one or more phase-owned controls or verification layers remain incomplete.
- **🟡** — planned, partially implemented, or awaiting required implementation/evidence.
- **⚪** — not yet reached or intentionally deferred.

A green phase status is an engineering implementation status only. It is never a statement that MandalFinance is legally compliant, certified, audited, or production-safe in every environment.

## 3. Required traceability

For every phase, the matrix should identify, where applicable:

- the PDP requirement;
- implementation files, routes, services, models, configuration, or infrastructure boundaries;
- the controlling policy/procedure document;
- automated tests and the CI gate;
- unresolved implementation or operational evidence;
- the next phase that owns the unresolved item.

Evidence must be specific enough that another engineer can independently reproduce the verification without relying on memory or an undocumented manual assertion.

## 4. Separation of implementation and operational evidence

Synthetic CI configuration, local development behavior, and repository tests must not be presented as proof of live production connectivity or deployment behavior.

Examples:

- CI Redis is evidence of rate-limit integration semantics, not proof of the production Redis provider or region.
- A production-shaped configuration simulation is evidence of fail-closed configuration rules, not proof that production secrets are correctly configured.
- Health endpoint tests are evidence of endpoint behavior, not proof of live production health.
- Payment/webhook unit tests are evidence of cryptographic verification logic, not proof of a live payment transaction.

Environment-specific evidence belongs to the PDP phase that explicitly owns it, especially Phase 32 and Phase 39.

## 5. Matrix maintenance rules

The matrix must be updated in the same hardening batch when a phase changes materially. A new security, privacy, financial, processor, browser, payment, document, or deployment control must not silently bypass the matrix.

When a later phase exposes a defect in an earlier control:

1. retain the historical evidence;
2. downgrade the affected phase if its completion criteria are no longer satisfied;
3. fix and test the defect;
4. restore PASS only after exact-head CI verification.

Do not mark a phase PASS merely because a documentation file exists.

## 6. DPDP-specific boundary

The matrix tracks engineering controls relevant to the Digital Personal Data Protection framework and related operational requirements. Legal applicability, commencement timing, contractual interpretation, regulatory advice, and organization-specific legal obligations require appropriate legal review.

The matrix must therefore distinguish:

- **implemented engineering control**;
- **documented procedure**;
- **automated verification**; and
- **environment/legal evidence still required**.

## 7. Release discipline

The matrix is a release-gate input, not a substitute for the final security review. Before deployment, the Release Gate must require every applicable PDP phase to have a defensible status and must reject unresolved P0 controls.

The final review must reconcile the matrix against the repository, CI evidence, production configuration, deployment evidence, and post-deployment verification rather than relying on the matrix alone.
