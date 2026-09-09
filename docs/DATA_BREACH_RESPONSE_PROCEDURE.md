# MandalFinance — Data Breach Response Procedure

**PDP phase:** 25 — Data Breach Response  
**Baseline:** `main`  
**Owner:** MandalFinance system owner / designated security lead  
**Review cadence:** At least annually and after every material incident or material architecture/provider change

This procedure is an engineering incident-response control. It does not replace legal advice, contractual obligations, payment-provider procedures, insurance requirements, or directions from a competent authority.

## 1. Purpose and scope

This procedure covers suspected or confirmed incidents involving:

- personal data;
- authentication credentials or sessions;
- financial records or payment state;
- uploaded financial documents;
- audit records or security logs;
- application infrastructure, databases, object storage, Redis, hosting, or payment integrations; and
- third-party processors handling MandalFinance data.

A suspected incident is handled as an incident until the investigation establishes that it is not a security or personal-data breach.

## 2. Mandatory response lifecycle

Every suspected breach follows this sequence:

**DETECT → INVESTIGATE → CONTAIN → ASSESS → IDENTIFY AFFECTED DATA → DOCUMENT → NOTIFY WHERE REQUIRED → REMEDIATE → REVIEW**

Do not skip directly from detection to deletion, database restoration, or public disclosure before preserving evidence and assessing scope.

## 3. Severity classification

| Severity | Example | Initial handling target |
|---|---|---|
| Critical | Confirmed unauthorized access to credentials, payment state, large-scale personal data, or production administrative control | Immediate containment; security lead and system owner engaged immediately |
| High | Confirmed unauthorized access to a user's personal/financial records, documents, or privileged function | Immediate containment and investigation |
| Medium | Limited suspected exposure with no evidence of successful unauthorized access | Investigate promptly; preserve evidence and monitor |
| Low | Security event with no evidence of personal-data or financial impact | Record, investigate, and close with rationale |

Severity may be raised at any time when new evidence increases the potential impact.

## 4. DETECT

Possible detection sources include:

- structured application logs and correlated request IDs;
- immutable audit events;
- authentication failures or unusual login activity;
- authorization failures and unexpected access patterns;
- document-storage anomalies;
- database alerts or integrity failures;
- payment/webhook anomalies;
- health or infrastructure alerts;
- reports from users, administrators, processors, or security researchers; and
- third-party provider incident notifications.

Record the first known detection time, reporter/source, affected environment, initial symptoms, and incident identifier. Do not put passwords, access tokens, document contents, payment credentials, or other secret material into the incident record.

## 5. INVESTIGATE

Create an incident record and preserve evidence before making destructive changes where practical.

Collect only evidence needed to determine scope and cause, such as:

- incident ID and timestamps;
- request/correlation IDs;
- relevant audit event IDs;
- affected route/function/resource identifiers;
- authentication and authorization outcomes;
- deployment/commit identifiers;
- relevant provider incident references;
- database/object identifiers rather than raw sensitive contents where possible;
- security-control configuration at the time of the event; and
- hashes or other integrity evidence for exported evidence.

Use the privacy-safe operational logs for telemetry. Application logging is intentionally designed not to record request bodies, query strings, cookies, authorization headers, or raw credentials. Audit logs provide append-only security/business-event history and integrity verification. Together these controls support investigation without intentionally collecting unnecessary sensitive content.

Do not copy production databases, full document sets, credentials, or payment secrets into tickets, chat, source control, or ad-hoc local files.

## 6. CONTAIN

Choose the least destructive containment that stops ongoing harm. Depending on the incident, actions may include:

1. revoke or rotate compromised credentials and sessions;
2. disable the affected account or privileged path;
3. block abusive IPs or tighten rate limits;
4. disable a vulnerable endpoint or integration;
5. isolate affected storage/database access;
6. pause affected financial operations when integrity cannot be trusted;
7. disable a compromised third-party integration; and
8. preserve affected infrastructure for investigation before rebuilding it where feasible.

Financial integrity takes priority over availability when continued processing could create incorrect or irreversible financial records.

## 7. ASSESS

Determine:

- whether the event is actually a security incident or personal-data breach;
- whether unauthorized access, alteration, disclosure, loss, or destruction occurred;
- whether financial records or payment state were affected;
- whether credentials, sessions, documents, or audit history were affected;
- the likely start and end time;
- affected systems and third parties;
- affected users/Data Principals or whether the population is still unknown;
- likely consequences and foreseeable risks; and
- containment/remediation status.

Use evidence rather than assumptions. If scope is unknown, record it as unknown and continue investigation.

## 8. IDENTIFY AFFECTED DATA

Classify affected information using the application's actual data inventory. At minimum consider:

| Data category | Examples | Investigation question |
|---|---|---|
| Account/contact data | Name, email, phone where collected | Was account/contact data accessed or exposed? |
| Authentication/security data | Password hashes, sessions, reset/security tokens | Could an attacker authenticate or impersonate a user? |
| Financial/application data | Donations, income, expenses, contributions, budgets, ledger records | Was financial integrity or confidentiality affected? |
| Supporting documents | Uploaded receipts, bills, evidence files | Were documents accessed, replaced, deleted, or exposed? |
| Payment data | Gateway order/payment identifiers and payment status | Was payment state altered or misrepresented? |
| Audit/security telemetry | Audit events, request IDs, IP/user-agent metadata | Was investigation evidence altered or exposed? |

Never treat payment-card credentials as MandalFinance-stored data merely because a payment gateway is integrated; the application must not store card numbers, CVV, UPI PINs, or equivalent payment credentials.

## 9. DOCUMENT

Maintain a controlled incident record containing, at minimum:

```text
Incident ID:
Opened at (UTC):
Detected at (UTC):
Reporter/source:
Environment:
Severity:
Status:
Incident owner:
Security lead:

Summary:
Affected systems:
Affected provider(s):
Known/possible affected Data Principals:
Known/possible affected data categories:
Estimated start/end time:
Root cause (when known):

Evidence references:
- Request/correlation IDs:
- Audit event IDs:
- Deployment/commit IDs:
- Provider incident IDs:

Containment actions:
Risk assessment:
Notifications required:
Notifications sent:
Remediation actions:
Post-incident review:
Closed at (UTC):
Closure approval:
```

Keep the record itself access-controlled. Store references and hashes instead of unnecessary copies of sensitive data.

## 10. NOTIFY WHERE REQUIRED

Notification decisions must be made by the responsible system owner with appropriate legal/compliance advice and against the law and rules in force for the incident date.

For India, the current MeitY-published **Digital Personal Data Protection Rules, 2025** provide a breach-notification framework under which a Data Fiduciary is required to promptly notify affected Data Principals and notify the Data Protection Board without delay; the detailed information to the Board is to be provided within 72 hours or a longer period permitted by the Board. The published rules also specify the information that must be included in the notification. The applicable commencement/enforcement timeline must be checked before relying on any particular obligation for a live incident.

The response team must therefore:

1. determine whether the relevant DPDP provisions are in force for the incident date;
2. identify whether the MandalFinance entity is acting as a Data Fiduciary for the affected processing;
3. identify applicable processor, payment, hosting, contractual, sectoral, or other notification duties;
4. prepare truthful, plain-language notifications based on confirmed facts;
5. state the nature, extent, timing, likely consequences, mitigation measures, recommended protective steps, and responsible contact where required;
6. preserve copies and timestamps of every notification; and
7. record any regulator-authorized extension, direction, or reasoned decision not to notify.

Do not delay urgent containment while debating the final wording of a notification.

## 11. REMEDIATE

Remediation must address both the immediate vulnerability and the underlying control failure. Examples:

- patch vulnerable code or dependencies;
- rotate credentials/secrets and invalidate sessions;
- correct authorization rules;
- restore or repair financial/document integrity using controlled workflows;
- tighten rate limits or security headers;
- correct logging/audit gaps;
- remove unnecessary data or access;
- update processor configuration;
- improve monitoring/detection; and
- add regression tests reproducing the incident's failure mode.

For financial corruption, do not silently rewrite finalized records. Use the application's correction/reversal and audit mechanisms.

## 12. REVIEW

After containment and remediation:

- establish the root cause and contributing factors;
- confirm affected scope and notification decisions;
- verify that containment is no longer required;
- run targeted regression/security tests;
- review whether logs and audit history were sufficient;
- review third-party processor handling where relevant;
- update policies, documentation, controls, and training;
- record lessons learned and owners/dates for follow-up actions; and
- formally close the incident only when evidence supports closure.

Material incidents must feed new tests or control improvements into the normal development workflow. A post-incident review must not weaken an existing financial or privacy control merely to make the incident disappear from metrics.

## 13. Evidence-retention and privacy rules

Incident evidence must be retained only for as long as necessary for investigation, legal/regulatory obligations, dispute handling, or other documented purposes. Apply the repository's retention schedule once Phase 17 is finalized.

Incident response must not become a reason to create a permanent shadow copy of production personal data. Use least-privilege access, minimal extracts, controlled storage, and documented destruction when the evidence is no longer required.

## 14. Roles and escalation

At minimum, the response requires named responsibility for:

- **Incident owner:** coordinates the lifecycle and maintains the incident record.
- **Security lead:** directs technical investigation and containment.
- **System/financial owner:** approves business-impact decisions, especially financial processing pauses or corrections.
- **Privacy/legal contact:** determines applicable notification and legal obligations.
- **Operations/deployment owner:** controls infrastructure, credentials, releases, and provider escalation.

One person may hold multiple roles in a small deployment, but the incident record must identify who is acting in each capacity.

## 15. Processor escalation

If a suspected breach involves Supabase, Razorpay, Vercel, Redis, or another processor, open the provider's security incident process in parallel and record its incident/reference number. Preserve the provider communication and determine whether provider contractual terms impose additional notification or cooperation duties.

The third-party processor register in `docs/THIRD_PARTY_PROCESSOR_REGISTER.md` is the starting point for identifying active providers and the data they may handle.

## 16. Readiness checklist

Before considering Phase 25 complete, the repository must demonstrate:

- [x] Formal DETECT → INVESTIGATE → CONTAIN → ASSESS → IDENTIFY AFFECTED DATA → DOCUMENT → NOTIFY WHERE REQUIRED → REMEDIATE → REVIEW lifecycle.
- [x] Severity and escalation guidance.
- [x] Evidence-preservation guidance tied to request correlation and audit history.
- [x] Privacy-safe incident-record rules.
- [x] Data-category impact assessment.
- [x] DPDP notification decision workflow with current-rule verification requirement.
- [x] Processor incident escalation.
- [x] Post-incident remediation and regression-test requirement.
- [x] Retention/destruction requirement for incident evidence.
- [x] Automated documentation consistency tests.

## 17. Authority and source note

This engineering procedure references the official Ministry of Electronics and Information Technology publication of the **Digital Personal Data Protection Rules, 2025** and its explanatory material. The explanatory note itself states that it is not part of the Rules and is not intended for legal interpretation. Live incidents must therefore be assessed against the operative law/rules and any later amendments, commencement notifications, Board directions, contracts, and other applicable obligations.

Primary government source: https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa

This procedure should be reviewed whenever the applicable legal framework or the application's processing architecture changes.
