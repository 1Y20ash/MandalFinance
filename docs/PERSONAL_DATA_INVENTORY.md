# MandalFinance Personal Data Inventory

Version: 1.0 | Review cadence: at least annually and after material feature/provider changes

| Data category | Purpose | Source | Basis / justification | Storage | Access | Retention | Deletion |
|---|---|---|---|---|---|---|---|
| Full name | Account identification and financial accountability | User | Core service / applicable legal and operational obligations | PostgreSQL | User; authorised staff by role | While account is active and as needed for financial/audit obligations | Corrected or removed/anonymised when no longer required, subject to mandatory records |
| Username | Authentication and account identity | User | Core service | PostgreSQL | User; authorised administrators | Account lifetime | Remove/anonymise during approved account closure where feasible |
| Email | Authentication, account communication and privacy requests | User | Core service / requested communication | PostgreSQL | User; authorised administrators | Account lifetime and justified operational period | Remove/anonymise after approved deletion, subject to obligations |
| Phone | Optional contact and financial identification where required | User/donor | Only where needed for the stated service purpose | PostgreSQL | User; authorised roles | Only while needed | Remove when purpose ends |
| Password hash | Authentication | User | Core service security | PostgreSQL | Application only | Account lifetime | Delete with account; never expose plaintext |
| Donation/contribution details | Financial accounting, receipts, reconciliation | User/donor/staff | Financial/accounting obligation and service operation | PostgreSQL | Finance-authorised roles; limited public aggregates | Per documented financial retention schedule | Preserve mandatory financial records; remove unnecessary personal linkage where lawful |
| Payment identifiers | Payment reconciliation and fraud investigation | Payment provider/application | Payment processing and financial reconciliation | PostgreSQL | Finance-authorised roles | Per financial/payment retention schedule | Remove where no longer required; preserve mandatory records |
| Uploaded documents | Evidence supporting financial operations | Authorised user/staff | Financial accountability | Private Supabase storage + PostgreSQL metadata | Authorised document roles | Per document retention schedule | Controlled deletion from storage and metadata after approval |
| Audit/security metadata | Security, accountability and incident investigation | Application | Legitimate security/operational necessity | PostgreSQL/logging infrastructure | Restricted administrators | Defined security-log schedule | Redact/minimise and delete after schedule unless required for investigation |
| IP address / user agent | Abuse prevention and security investigation | Application request | Security necessity | Audit/log infrastructure | Restricted administrators | Defined security-log schedule | Delete/anonymise after schedule |
| Session information | Secure authentication | Application/browser | Core service security | Secure server session/cookie mechanism | Application | Session lifetime | Automatic expiry/invalidation |

## Minimisation rules

- Do not add personal-data fields without a documented purpose and retention owner.
- Do not copy personal data into audit descriptions when an identifier is sufficient.
- Public transparency uses aggregated financial information and must not expose donor contact details or private identifiers.
- Optional analytics/communications are separate consent purposes and must not be bundled with core service access.
