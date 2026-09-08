# MandalFinance PDP Compliance Matrix

**Baseline:** `feat/premium-glass-ui` @ `3572d43201b333cb74abafe647cfa5f05c4a8712`  
**Hardening branch:** `feat/pdp-full-hardening`  
**Principle:** Money → Transaction → Supporting Document → User → Approval → Payment → Audit History

This is an engineering implementation matrix, not a legal, statutory, accounting, or security certification.

| PDP phase | Current state | Evidence in repository | Remaining work | Priority |
|---|---|---|---|---|
| 0. Baseline / architecture lock | 🟢 | Baseline matrix + CI-verified hardening branches | Keep matrix synchronized with future releases | P0 |
| 1. Foundation / financial integrity | 🟢/🟡 | Decimal/Numeric money fields, central ledger, event/FY locking, duplicate-reference guards | Complete production DB invariant verification | P0 |
| 2. Authentication / dynamic RBAC | 🟢/🟡 | Flask-Login, dynamic roles/permissions, dedicated `finance.view`/`finance.manage`, global finance-control authorization guard | Assign dedicated permissions to operational roles and complete object-level authorization tests | P0 |
| 3. Mandal / event / ledger core | 🟢/🟡 | Event/FY locking and financial guard | Expand event/FY mutation tests across every module | P0 |
| 4. Income / donations / receipts | 🟢/🟡 | Donation duplicate external-reference checks, evidence enforcement, central-ledger posting | Complete receipt/report lifecycle and production evidence policy configuration | P0 |
| 5. Expenses / vendors / approval / payment | 🟢/🟡 | Submit → approve → pay, SOD, evidence gate, central ledger | Expand vendor lifecycle and negative-path matrix | P0 |
| 6. Sponsorship / member / budget | 🟢/🟡 | Sponsorship/member receipt lifecycle, target/commitment limits, budget DRAFT → APPROVED → REVISED workflow, approval SOD | Add richer sponsor/member master-data and document/receipt UI | P1 |
| 7. Cash / bank / UPI / reconciliation | 🟢/🟡 | Reconciliation records plus statement-line import, unique matching, unmatched blocking, finalization gate | Add CSV/Excel bank statement adapters and transfer-specific matching UX | P0 |
| 8. Document vault / versioning / integrity | 🟡 | SHA-256, versions, protected access | Production storage hardening and full object-authorization matrix | P0 |
| 9. Evidence / timeline / evidence packs | 🟢/🟡 | EvidenceRule enforcement on expense, contribution, offline/online donation payment paths | Configure production rules and add document pre-payment workflows where required | P0 |
| 10. Audit / correction / reversal / reporting | 🟢/🟡 | Audit events for hardening actions, correction/reversal infrastructure | Full mutation coverage and reconstruction tests | P0 |
| 11. Dashboard / analytics / transparency | 🟡 | Existing dashboard/reports/notifications | Unified search, public transparency and notification completeness | P1 |
| 12. Security / financial-integrity testing | 🟢/🟡 | Dedicated hardening test matrix for RBAC, duplicates, over-collection, reconciliation and evidence | Expand horizontal/vertical object access, CSRF/API authorization and locked-record cases | P0 |
| 13. UI / UX / accessibility / performance | 🟡 | Premium glass UI and responsive templates | Full accessibility/mobile/performance audit | P1 |
| 14. Production / release verification | 🔴 | Repeatable CI migration/regression verification | Production DB/storage/secrets/backups/deployment smoke tests and E2E reconstruction | P0 |

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

## Hardening delivered in the current branch

### RBAC hardening
All `/finance-controls` routes now pass through a second server-side authorization layer. Non-admin reads require `finance.view`; mutations require `finance.manage`. Existing handler-level checks remain in place as defense in depth. `budget.approve` is a dedicated permission for budget approval.

### Reconciliation workflow
Reconciliation now supports statement-line import, unique line references, matching by external reference or account/date/amount, duplicate-match prevention, unmatched-line blocking and finalization only when the ledger/statement difference is zero.

### Sponsorship/member/budget lifecycle
Sponsorship/member receipts validate active accounts, payment modes, external references, commitment/target limits and evidence before ledger posting. Budgets now have explicit DRAFT/APPROVED/REVISED lifecycle state, revision reasons, approval identity/time, segregation of duties, and ledger-derived actuals.

### Evidence enforcement
Evidence checks are enforced at the payment/posting boundary for expenses, contribution receipts, offline donations and gateway-confirmed donations. Missing required evidence prevents the ledger transaction from being finalized.

### Financial-integrity/security tests
`tests/test_pdp_hardening.py` covers dedicated finance permissions, duplicate external references, contribution over-collection, duplicate reconciliation periods, statement-line matching, unmatched reconciliation blocking, donation evidence blocking and budget approval separation.

## Verification gate

A phase is not considered complete merely because its normal-path test passes. The implementation gate is:

**PLAN → IMPLEMENT → TEST → FIX → VERIFY → DOCUMENT → NEXT PHASE**

CI must remain green after every hardening batch. A green CI run is evidence that the committed test suite passes; it is not by itself a production compliance certification.
