# MandalFinance Privacy Notice

**Version:** 1.0  
**Effective date:** 9 September 2026  
**Owner:** Ganesh Mandal / designated privacy-grievance contact  
**Review:** At least annually and whenever processing purposes, data categories, material providers, or rights procedures change.

## 1. Controller / fiduciary identity

MandalFinance is operated for the Ganesh Mandal. The Mandal is responsible for deciding the purposes and means of processing personal data through the application and for maintaining appropriate governance, privacy and grievance contacts.

The Mandal must keep the designated privacy/grievance contact details current wherever this notice is published.

## 2. Personal data processed

MandalFinance processes only data needed for its stated purposes, including:

- account data: full name, username, email and optional phone;
- authentication/security data: password hash, session and security metadata;
- financial data: donation/contribution details, transaction references and payment identifiers needed for accounting and reconciliation;
- authorised financial documents and their metadata;
- limited request, IP-address and user-agent metadata where needed for security and incident investigation.

The standard offline donation workflow does not require donor PAN, postal address or donor email. Optional information must have a specific operational purpose before collection.

## 3. Purposes

Personal data is processed to:

1. provide and secure user accounts;
2. operate Mandal financial-management functions;
3. record, reconcile and evidence financial transactions;
4. process and verify online payments where enabled;
5. issue and maintain financial records and receipts;
6. secure the application, prevent abuse and investigate incidents;
7. handle Data Principal privacy requests and grievances; and
8. comply with applicable legal, accounting, tax, security and governance obligations.

## 4. Basis / justification

Core processing is limited to what is necessary for the requested service, security/accountability controls, or applicable obligations. Optional processing that appropriately relies on consent is separated from the core service and is recorded with purpose, notice version, source and timestamps.

## 5. Processors and recipients

Depending on the enabled features, limited personal data may be processed by:

- Razorpay for online payment processing;
- configured PostgreSQL/private storage infrastructure for application data and financial evidence;
- Redis or equivalent infrastructure for production rate limiting/security;
- monitoring or communications providers only when actually enabled for the relevant purpose.

The current processor register is maintained separately and must match the providers actually used by the deployed application.

## 6. Payment data

MandalFinance does not request payment credentials such as card PINs, CVVs or banking passwords. When an online payment provider is enabled, the application verifies payment responses server-side and stores only identifiers and status information needed for reconciliation, accounting, security and investigation.

## 7. Documents

Financial evidence uploaded to MandalFinance is intended for authorised use only. Documents should be relevant to the associated financial operation. Protected storage, access control and controlled deletion are applied according to the Document Security and Data Deletion procedures.

## 8. Retention

Personal data is retained only as long as necessary for the relevant purpose and applicable financial, legal, security or audit requirements. Detailed category-specific periods are maintained in the Retention Schedule. A deletion request does not automatically override a mandatory retention requirement.

## 9. Security

MandalFinance applies layered technical and organisational safeguards including authentication, role-based access control, CSRF protection, rate limiting, protected document storage, payment verification, audit logging, secure cookies and production configuration controls. Security is reviewed through testing and incident-response procedures.

## 10. Data Principal rights and privacy requests

Authenticated users may submit requests for:

- access to applicable personal data;
- correction of inaccurate data;
- deletion where applicable;
- withdrawal of optional consent; and
- privacy grievances.

Requests are handled through the documented workflow: **REQUESTED → IDENTITY VERIFIED → REVIEWED → PROCESSED → COMPLETED**, with rejection where justified. Identity verification may be required before disclosure or action.

## 11. Consent withdrawal

Optional consent can be withdrawn through the Privacy Center. Withdrawal is recorded and does not invalidate processing lawfully completed before withdrawal. Necessary core-service, financial, security or legally required processing is not treated as optional consent processing.

## 12. Grievance handling

Privacy grievances are recorded and reviewed through the Privacy Center and the Mandal's designated grievance process. The Mandal must maintain an accessible contact channel outside the application and keep the published contact information current.

## 13. Changes to this notice

Material changes to processing purposes, data categories, processors or rights handling require review and a new notice version where appropriate. Where optional consent is affected, the consent record/versioning process must be followed.

**Last reviewed:** 9 September 2026.
