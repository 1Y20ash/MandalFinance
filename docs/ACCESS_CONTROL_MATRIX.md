# MandalFinance Access Control Matrix

**Version:** 1.0  
**Effective:** 9 September 2026  
**Scope:** Application routes, financial data, personal data, documents, privacy workflows and administrative functions.

## 1. Authorization principles

MandalFinance uses server-side authorization as the security boundary. A hidden button, URL obscurity, client-side role value, or submitted role/permission ID is never treated as authorization.

Every protected operation must satisfy:

1. An authenticated session is present.
2. The account is active and approved.
3. The route/service applies the required permission or administrative policy on the server.
4. Object identifiers supplied by the client are resolved server-side and must not bypass the route's authorization boundary.
5. Authorization failures are denied with HTTP 403 and recorded using minimal audit metadata where practical.
6. Administrative operations require administrator authority and are not granted merely because a user has a finance permission.

The centralized `permission_required()` and `admin_required()` decorators enforce these rules for route-level access. Financial-control routes additionally have a second server-side guard.

## 2. Role definitions

| Role | Purpose | Privilege level |
|---|---|---|
| Public | Unauthenticated visitor | Public information only |
| Volunteer | Routine festival/account activity | Least privilege; no approvals, administration or financial-control writes |
| Treasurer | Financial operations and controlled finance management | Finance operations; no user/role administration |
| Secretary | Operational oversight and approved administrative functions | Operational oversight; no unrestricted finance-control writes unless explicitly assigned |
| Admin | System administration | User/role/permission administration and controlled system functions |

> **Implementation note:** The application currently contains system roles such as `Super Admin` and `Volunteer`, plus dynamically managed roles. The matrix above is the target authorization model. Dynamic roles must be assigned only the permissions appropriate to their documented responsibility.

## 3. Permission model

| Permission | Capability | Minimum intended role |
|---|---|---|
| `dashboard.view` | View authenticated financial/dashboard summary | Volunteer |
| `donation.view` | View donation records | Volunteer |
| `donation.create` | Record offline donation | Volunteer |
| `donation.receipt` | Generate confirmed donation receipt | Treasurer / authorized finance role |
| `expense.view` | View expenses | Volunteer / finance role |
| `expense.create` | Submit an expense | Volunteer |
| `expense.approve` | Approve an expense | Treasurer / authorized approver |
| `expense.reject` | Reject an expense | Treasurer / authorized approver |
| `expense.pay` | Pay an approved expense | Treasurer / authorized finance role |
| `finance.view` | View finance-control information | Treasurer / Secretary as assigned |
| `finance.manage` | Create/change controlled finance records and reconciliation controls | Treasurer |
| `budget.approve` | Approve budgets | Treasurer / authorized approver |
| `document.view` | View authorized documents | Volunteer / assigned role |
| `document.upload` | Upload authorized documents | Volunteer / assigned role |
| `user.manage` | Manage user accounts | Admin |
| `role.manage` | Manage roles and permission assignments | Admin |
| `audit.view` | Review audit records | Admin / explicitly authorized audit role |
| `privacy.manage` | Process Data Principal privacy requests | Admin / designated privacy role |

Only permissions actually registered in the database may authorize an operation. New permissions must be documented before use.

## 4. Administrative boundary

`is_admin` is a dedicated administrative boundary and is not equivalent to an ordinary business permission. Administrative routes therefore require explicit administrator status. System roles cannot be modified or deleted through the normal role-management interface.

Role assignment is performed server-side. Submitted role IDs are resolved against database rows, and the resulting role set is what is persisted; client-side labels or hidden fields do not confer privilege.

## 5. Object-level authorization / BOLA controls

For routes containing an object identifier, authorization is evaluated before the object is used for a privileged operation. Tests must cover attempts to substitute another user's or another protected object's ID.

Particular attention is required for:

- donation IDs and receipts;
- expense IDs and payment/approval actions;
- document IDs and downloads/deletions;
- privacy request IDs;
- reconciliation/control IDs;
- user IDs and role assignment targets;
- payment/order identifiers and webhook event identifiers.

A route must never rely on the fact that an ID is syntactically valid or that the object exists.

## 6. Separation of duties

Financial permissions are intentionally separated:

- viewing is distinct from management;
- expense submission is distinct from approval;
- approval is distinct from payment;
- finance-control management is distinct from ordinary donation/expense creation;
- user/role administration is distinct from financial authority.

Where a business workflow requires stronger separation, the service layer must enforce it in addition to route-level permissions.

## 7. UI rule

The UI may hide controls that the current user cannot use, but UI visibility is only a usability feature. Every corresponding POST/GET operation remains protected by server-side authorization.

## 8. Change control

Changes to roles, permissions, protected routes, or separation-of-duty rules must include:

- an update to this matrix;
- route/service authorization tests;
- negative authorization tests;
- IDOR/BOLA regression tests where an object identifier is involved;
- auditability review;
- CI verification before release.
