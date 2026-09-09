# MandalFinance — Initial Personal Data Inventory

This is an engineering inventory for the PDP audit. It is not a legal determination of applicability.

| Data category | Examples observed | Primary purpose to validate | Required review |
|---|---|---|---|
| Account identity | full name, username, email, phone | account management/authentication | minimisation, notice, retention |
| Authentication | password hash, session/auth state | secure authentication | security, retention, logging |
| Donor identity | donor name, phone, email | donation processing/receipt | purpose, notice, retention |
| Donor details | address, PAN where collected | donation/financial records | necessity, access, retention |
| Payment data | order/payment/transaction identifiers | payment verification/reconciliation | minimisation, processor disclosure |
| Financial records | donation/expense/ledger records linked to people | accounting/transparency | RBAC, integrity, retention |
| Uploaded documents | receipts/evidence/supporting documents | financial evidence | private storage, authorization, retention |
| Audit/security data | IP, user-agent, actor identity, event details | security/accountability | minimisation, retention |
| Operational identifiers | object IDs, request/event IDs | integrity/traceability | public exposure review |

## Next audit tasks
- Map every field to its exact model and route.
- Identify all reads, writes, exports and public responses.
- Identify whether each field is required or optional.
- Define purpose and retention before implementing deletion.
- Identify processor/third-party exposure.
- Add tests preventing cross-user disclosure.
