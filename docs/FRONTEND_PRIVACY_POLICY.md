# Phase 27 — Frontend Privacy Policy

**Status:** Implemented and subject to CI verification  
**Scope:** Browser-side behavior, client storage, service-worker caching, public templates, and third-party browser resources.

## 1. Privacy boundary

MandalFinance uses server-rendered HTML and secure server-side sessions. Browser JavaScript must not create a second client-side source of truth for financial records, authentication state, donor records, payment credentials, supporting documents, or administrative data.

The browser may receive only the information necessary to render the current page and complete the current user action.

## 2. Client-side storage rules

### Permitted

- `sessionStorage` may be used only for short-lived, non-sensitive UI state such as whether the optional PWA installation prompt was already shown during the current browser session.
- In-memory JavaScript variables may temporarily hold transient UI state such as a deferred browser installation prompt.

### Prohibited

The application must not persist the following in `localStorage`, `sessionStorage`, IndexedDB, Cache Storage, Web SQL, cookies created by application JavaScript, or other browser persistence mechanisms:

- passwords, password-reset tokens, session identifiers, CSRF tokens, authentication tokens, API keys, or secrets;
- donor names, phone numbers, email addresses, addresses, or other personal-data records;
- payment credentials, Razorpay secrets, payment signatures, or gateway authentication material;
- financial transaction records, private ledger details, administrative records, audit logs, or sensitive reports;
- document contents, document URLs containing authorization material, or evidence-vault data.

Server authentication/session cookies remain server-controlled and must not be copied into JavaScript storage.

## 3. Service-worker and offline-cache boundary

The service worker is deliberately limited to public, non-sensitive application shell resources and static assets. It may cache:

- the public landing/transparency page;
- the public donation page only if it is explicitly verified to contain no session-bound or security-sensitive token; and
- static CSS, manifest, and public application icons.

**Current control:** the public donation page contains a server-generated CSRF token, so it is **not** eligible for precaching. This prevents a session-bound CSRF value from being placed in Cache Storage as an installation-time asset.

The service worker must not cache authenticated pages, dashboards, financial records, reports, audit logs, evidence documents, payment responses, or arbitrary application responses. Navigation requests use the network first and only fall back to explicitly approved public shell resources. Non-GET requests are never handled by the cache strategy.

When public page content changes, the cache version must be incremented so stale public content can be retired deterministically.

## 4. Third-party browser resources

The application currently references browser-delivered resources such as Google Fonts, Bootstrap via jsDelivr, and Font Awesome via cdnjs. These resources are presentation dependencies, not application data processors by design. Application JavaScript must not send MandalFinance records to these providers.

Any future analytics, advertising, tracking, session-replay, chat, telemetry, or other browser SDK must undergo the Third-Party Processor Register and privacy review before enablement.

## 5. Payment pages

Payment initiation must keep donor/payment data within the minimum required server and gateway flow. Browser code must never contain Razorpay secret credentials. Payment verification remains server-side.

Client-side code must not log payment responses, signatures, donor contact details, or gateway credentials to the console.

## 6. PWA privacy

The optional installation prompt may use `sessionStorage` only to suppress repeated UI prompts during a session. It must not use browser persistence for identity, financial data, authentication, payment information, or documents.

The service worker's offline behavior is a public-content availability feature, not an offline copy of the financial application.

## 7. Review requirements

Review the frontend privacy boundary whenever:

1. a new browser storage mechanism is introduced;
2. a new JavaScript SDK or third-party resource is added;
3. an authenticated page becomes available offline;
4. payment or document flows change;
5. a new API endpoint is consumed from JavaScript; or
6. analytics, monitoring, chat, advertising, or tracking is proposed.

Phase 27 is an engineering privacy control, not a legal certification. The Personal Data Inventory, Consent, Data Principal Rights, Retention, and Processor Register remain authoritative for their respective PDP phases.
