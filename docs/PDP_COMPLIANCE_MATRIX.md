# MandalFinance PDP Compliance Matrix

**Baseline:** `main`  
**Principle:** Money → Transaction → Supporting Document → User → Approval → Payment → Audit History

This is an engineering implementation matrix, not a legal, statutory, accounting, or security certification.

| PDP phase | Current state | Evidence in repository | Remaining work | Priority |
|---|---|---|---|---|
| 0. Baseline / architecture lock | 🟢 | Baseline matrix + CI-verified hardening branches | Keep matrix synchronized with future releases | P0 |
| 1. Foundation / financial integrity | 🟢/🟡 | Decimal/Numeric money fields, central ledger, event/FY locking, duplicate-reference guards | Complete production DB invariant verification | P0 |
| 2. Authentication / dynamic RBAC | 🟢/🟡 | Flask-Login, dynamic roles/permissions, finance-control authorization guard | Expand object-level authorization tests | P0 |
| 3. Mandal / event / ledger core | 🟢/🟡 | Event/FY locking and financial guard | Expand event/FY mutation tests across every module | P0 |
| 4. Income / donations / receipts | 🟢/🟡 | Duplicate external-reference checks, evidence enforcement, central-ledger posting | Complete receipt/report lifecycle and production evidence policy configuration | P0 |
| 5. Expenses / vendors / approval / payment | 🟢/🟡 | Submit → approve → pay, SOD, evidence gate, central ledger | Expand vendor lifecycle and negative-path matrix | P0 |
| 6. Sponsorship / member / budget | 🟢/🟡 | Receipt lifecycle, target/commitment limits, budget workflow, approval SOD | Add richer sponsor/member master-data and document/receipt UI | P1 |
| 7. Cash / bank / UPI / reconciliation | 🟢/🟡 | Reconciliation records, statement-line matching and finalization gates | Add richer bank statement adapters and transfer UX | P0 |
| 8. Document vault / versioning / integrity | 🟡 | SHA-256, versions, protected access | Production storage hardening and full object-authorization matrix | P0 |
| 9. Evidence / timeline / evidence packs | 🟢/🟡 | EvidenceRule enforcement on payment/posting boundaries | Configure production rules and expand evidence workflows | P0 |
| 10. Audit / correction / reversal / reporting | 🟢 | Audit service, transactional audit writes, immutable ORM/database controls, SHA-256 row integrity, authentication security events, admin audit trail | Continue adding coverage when new privileged business events are introduced | P0 |
| 11. Dashboard / analytics / transparency | 🟡 | Existing dashboard/reports/notifications | Unified search, public transparency and notification completeness | P1 |
| 12. Security / financial-integrity testing | 🟢/🟡 | Dedicated hardening/security test matrix plus audit-integrity tests | Expand horizontal/vertical object access and locked-record cases | P0 |
| 13. UI / UX / accessibility / performance | 🟡 | Premium glass UI and responsive templates | Full accessibility/mobile/performance audit | P1 |
| 14. Production / release verification | 🟡 | Repeatable CI migration/regression verification, production preflight and structured application logging | Production DB/storage/secrets/backups/deployment smoke tests and E2E reconstruction | P0 |

## Absolute financial integrity rules

1. Store monetary values as `NUMERIC/DECIMAL`; normalize with Python `Decimal`.
2. Never trust client-supplied totals, status transitions, permissions, identities, or approval state.
3. Never silently delete finalized financial records; use correction/reversal workflows.
4. A finalized document replacement must preserve a version, reason, uploader, timestamp, and SHA-256 hash.
5. No expense payment before approval.
6. No self-approval for normal expense/correction/budget approval workflows.
7. Every finalized payment must create exactly one corresponding ledger transaction.
8. External payment references must not be reusable.
9. Locked events/financial years must reject financial mutations.
10. Reports, dashboards, account balances, reconciliations, and evidence packs must derive from one authoritative ledger invariant.
11. A reconciliation cannot be finalized while statement lines are unmatched or the balance difference is non-zero.
12. Budget actuals are derived from finalized ledger transactions rather than duplicated module totals.
13. Audit history is append-only and tamper-evident; security-sensitive events must not be silently discarded.

## Audit logging hardening

Phase 21 adds a dedicated immutable audit layer. `AuditLog` now carries a UUID event identifier, outcome, request correlation ID and SHA-256 integrity digest. The application rejects ORM updates/deletes, while PostgreSQL receives a database trigger that rejects direct `UPDATE`/`DELETE` operations. `AuditService` serializes structured metadata as JSON, redacts credential-like keys, supports atomic `commit=False` writes, and provides integrity verification.

Authentication now records successful logins, failed credential attempts and blocked logins without storing passwords or raw credential material. The administrator audit page exposes the event outcome, request ID and digest prefix for investigation and traceability.

## Verification gate

A phase is not considered complete merely because its normal-path test passes. The implementation gate is:

**PLAN → IMPLEMENT → TEST → FIX → VERIFY → DOCUMENT → NEXT PHASE**

CI must remain green after every hardening batch. A green CI run is evidence that the committed test suite passes; it is not by itself a production compliance certification.
