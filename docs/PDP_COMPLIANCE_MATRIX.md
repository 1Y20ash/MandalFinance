# MandalFinance PDP Compliance Matrix

**Baseline:** `feat/premium-glass-ui` @ `3572d43201b333cb74abafe647cfa5f05c4a8712`  
**Hardening branch:** `feat/pdp-compliance-hardening`  
**Principle:** Money → Transaction → Supporting Document → User → Approval → Payment → Audit History

This is an engineering implementation matrix, not a legal, statutory, accounting, or security certification.

| PDP phase | Current state | Evidence in repository | Remaining work | Priority |
|---|---|---|---|---|
| 0. Baseline / architecture lock | 🟡 | Existing models, services, tests, CI; this matrix now records the baseline | Keep this matrix updated as phases close | P0 |
| 1. Foundation / financial integrity | 🟢/🟡 | Decimal/Numeric money fields, central ledger, event/FY locking, integrity migrations | Complete cross-model invariant tests and production DB verification | P0 |
| 2. Authentication / dynamic RBAC | 🟡 | Flask-Login, roles/permissions, password hashing, registration approval | Audit every financial-control route for least-privilege read/write access | P0 |
| 3. Mandal / event / ledger core | 🟡 | Event/FY lifecycle and central transactions | Enforce event/FY context consistently across every financial mutation | P0 |
| 4. Income / donations / receipts | 🟡 | Donation gateway verification, sponsorship/member receipts, ledger posting | Complete evidence linkage, duplicate-payment cases, reconciliation and receipt lifecycle | P0 |
| 5. Expenses / vendors / approval / payment | 🟡 | Submit → approve → pay workflow, segregation-of-duties checks, ledger posting | **Implemented in this branch:** evidence rules are checked server-side before expense payment | P0 |
| 6. Sponsorship / member / budget | 🟡 | Sponsorship/member models and budget foundation | Complete master data, payment history, document/receipt lifecycle, approval/revision workflow | P1 |
| 7. Cash / bank / UPI / reconciliation | 🔴/🟡 | Account model and reconciliation records/service | Statement import, transaction matching, unmatched workflow, adjustment workflow and full transfer support | P0 |
| 8. Document vault / versioning / integrity | 🟡 | SHA-256, document versions, protected download, replacement/integrity routes | Production storage hardening and comprehensive authorization/object-access tests | P0 |
| 9. Evidence / timeline / evidence packs | 🟡 | EvidenceRule, evidence checking, timeline and evidence-pack infrastructure | Expand rules to all payment paths and enforce completeness before finalization | P0 |
| 10. Audit / correction / reversal / reporting | 🟡 | AuditLog, correction requests, reversal transactions, reports | Verify audit coverage for every mutation and expand reconstruction tests | P0 |
| 11. Dashboard / analytics / transparency | 🟡 | Dashboard, analytics endpoint, reports, public donation flow | Notifications/search/public transparency/analytics completeness | P1 |
| 12. Security / financial-integrity testing | 🟡 | Green CI, CSRF, rate limiting, RBAC, gateway verification, negative tests | Add horizontal/vertical authorization, duplicate payment, locked-record and object-access test matrix | P0 |
| 13. UI / UX / accessibility / performance | 🟡 | Premium glass UI work and responsive templates | Full accessibility, mobile, performance and error-state audit | P1 |
| 14. Production / release verification | 🔴 | CI provides repeatable regression evidence | Production DB, storage, secrets, backups, deployment smoke tests and E2E financial reconstruction | P0 |

## Absolute financial integrity rules

1. Store monetary values as `NUMERIC/DECIMAL`; normalize with Python `Decimal`.
2. Never trust client-supplied totals, status transitions, permissions, identities, or approval state.
3. Never silently delete finalized financial records; use correction/reversal workflows.
4. A finalized document replacement must preserve a version, reason, uploader, timestamp, and SHA-256 hash.
5. No expense payment before approval.
6. No self-approval for normal expense/correction workflows.
7. Every finalized payment must create exactly one corresponding ledger transaction.
8. External payment references must not be reusable.
9. Locked events/financial years must reject financial mutations.
10. Reports, dashboards, account balances, reconciliations, and evidence packs must derive from one authoritative ledger invariant.

## Hardening delivered on this branch

### Payment → Evidence enforcement
`ExpenseService.pay_expense()` now calls the server-side evidence-rule engine before creating the disbursement ledger transaction. If an active rule requires evidence and the linked documents are incomplete, payment is rejected and the expense remains `APPROVED` with no transaction created.

A regression test covers this negative path in `tests/test_financial_controls.py`.

## Verification gate

A phase is not considered complete merely because its normal-path test passes. The implementation gate is:

**PLAN → IMPLEMENT → TEST → FIX → VERIFY → DOCUMENT → NEXT PHASE**

CI must remain green after every hardening batch. A green CI run is evidence that the committed test suite passes; it is not by itself a production compliance certification.
