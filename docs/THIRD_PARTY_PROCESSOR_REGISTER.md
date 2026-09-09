# MandalFinance — Third-Party Processor Register

**PDP phase:** 24 — Third-Party Processors  
**Baseline:** `main`  
**Review status:** Engineering register; contractual/legal terms must be verified by the Mandal before production use.

This register records third parties that currently process, host, store, transmit, or deliver MandalFinance data or browser resources. It is intentionally broader than a list of formal "processors": browser-facing infrastructure and content delivery services are included where a user's browser necessarily connects to them.

## 1. Current processor/service register

| Provider / service | Role | Data shared or potentially exposed | Purpose | Storage/location | Security / minimisation control | Contract / terms evidence | Status |
|---|---|---|---|---|---|---|---|
| **Supabase** | Database/object-storage infrastructure | Account/application records stored in Supabase; uploaded financial documents; document object paths and metadata | Application database and private financial-evidence storage | Provider-managed infrastructure; exact project region is deployment-specific and must be recorded in production configuration | Private storage required; service-role key server-side only; random object paths; authorization before access; no public bucket dependency | [Supabase DPA](https://supabase.com/downloads/docs/Supabase%2BDPA%2B250805.pdf) | **Active** |
| **Razorpay** | Payment processor/gateway | Donation/payment information required for payment processing; donor name is sent as an order note; Razorpay Checkout may receive donor name, email and phone as prefill data; gateway order/payment identifiers | Online donation payment processing and payment verification | Razorpay-managed payment infrastructure; exact applicable processing/storage location governed by Razorpay terms | Server creates orders; amount/order are server-controlled; payment signatures and webhooks verified; no card credentials stored by MandalFinance | [Razorpay Privacy Policy](https://razorpay.com/privacy-policy/) and [Razorpay Buyer Privacy Notice](https://razorpay.com/buyer-privacy-notice/) | **Active** |
| **Vercel** | Application hosting / serverless execution | HTTP request data required to serve the application, including IP/network metadata and application payloads processed by the hosted server; deployment/service metadata | Host and execute MandalFinance | Vercel-managed infrastructure; location depends on deployment configuration | HTTPS; secure cookies in production; no secrets in frontend; application data intended for PostgreSQL/Supabase rather than local filesystem in production | [Vercel DPA](https://vercel.com/legal/dpa) and [Vercel Privacy Notice](https://vercel.com/legal/privacy-notice) | **Active** |
| **Managed Redis provider** | Shared persistent rate-limit storage | Rate-limit keys/counters; current application keying uses remote IP address for the default limiter and endpoint-specific IP/account keys where configured | Distributed abuse protection across application instances | Deployment-specific managed Redis service; provider identity and region must be recorded before production | No application secrets or financial records are intentionally stored in Redis; production rejects memory-only storage | Provider-specific DPA/terms must be recorded once the production Redis provider is selected | **Required infrastructure; provider TBD in repository** |
| **Razorpay Checkout.js** | Browser payment UI / payment resource | Browser request metadata plus payment information entered/used during checkout | Secure client-side payment collection | Razorpay-managed browser/payment infrastructure | Only public Razorpay key/order information is sent to the browser; secret key remains server-side; payment response is verified server-side | Razorpay terms/privacy apply | **Active when Razorpay is enabled** |
| **Google Fonts** | Browser font resource provider | Browser network metadata (such as IP address/user-agent) when fonts are fetched | Typography | Google-managed CDN | No MandalFinance application record or financial payload is intentionally sent; resource is loaded only for presentation | Google privacy/terms apply | **Active browser dependency** |
| **jsDelivr** | Browser CDN for Bootstrap assets | Browser network metadata when assets are fetched | Bootstrap CSS/JS delivery | CDN infrastructure | No MandalFinance application payload is intentionally sent | Provider terms/privacy apply | **Active browser dependency** |
| **cdnjs / Cloudflare** | Browser CDN for Font Awesome assets | Browser network metadata when assets are fetched | Icon/font asset delivery | CDN infrastructure | No MandalFinance application payload is intentionally sent | Provider terms/privacy apply | **Active browser dependency** |

## 2. Third parties not currently enabled

The following categories are **not currently configured as application processors** and must not be introduced without updating this register first:

- Email delivery provider
- SMS/WhatsApp provider
- Analytics platform
- Advertising/tracking platform
- Error-monitoring platform that receives application/user data
- Customer-support/chat platform
- Additional payment gateway
- Additional cloud object-storage provider

If any of these are introduced, the implementation must first complete a minimum-data-sharing review, update the privacy notice where applicable, and add the provider to this register.

## 3. Minimum-data-sharing rules

### Supabase

- Store only data required by the application's database and document-storage functions.
- Keep the storage bucket private.
- Never expose the Supabase service-role key to the browser.
- Do not use public object URLs for private financial evidence.
- Store opaque/randomized object names rather than original filenames as storage object identifiers.

### Razorpay

- Send only payment-required information to the gateway.
- The server remains authoritative for donation amount, order identity and payment state.
- Do not send the MandalFinance password, session token, CSRF token, internal audit data, or unrelated financial records to Razorpay.
- Do not store card numbers, CVV, UPI PINs, or other payment credentials in MandalFinance.
- Verify gateway responses and webhooks server-side before financial posting.

### Vercel

- Treat hosted requests and service-generated metadata as potentially containing personal data.
- Do not put secrets or private database credentials in client bundles.
- Do not depend on the serverless filesystem for authoritative financial/document storage.
- Keep application logs privacy-safe.

### Redis

- Use Redis only for rate-limit state.
- Do not place passwords, tokens, document contents, payment credentials, or financial records into rate-limit values.
- Keep production rate-limit storage persistent/shared.
- Record the actual production provider and region during Phase 32 production-configuration verification.

### Browser resource CDNs

- Treat external CSS/JS/font resources as a privacy consideration because a browser request can expose network metadata.
- Do not include personal-data query strings or application data in third-party resource URLs.
- A future privacy-hardening pass may self-host these assets if reducing browser-side third-party disclosure becomes a requirement.

## 4. Data-flow summary

```text
MandalFinance application
        |
        +---- PostgreSQL / Supabase ---- application + financial records
        |
        +---- Supabase Storage --------- private financial documents
        |
        +---- Razorpay ------------------ online payment processing
        |
        +---- Shared Redis -------------- rate-limit state only
        |
        +---- Vercel -------------------- application hosting/execution
        |
        +---- Browser CDNs -------------- presentation assets only
```

## 5. Operational processor controls

Before production, the responsible administrator must verify and record:

1. Supabase project/region and applicable DPA/terms.
2. Razorpay merchant/account configuration and applicable terms/privacy notice.
3. Vercel project/team and applicable DPA/terms.
4. The exact managed Redis provider, service/region, and applicable DPA/terms.
5. Whether any additional monitoring, analytics, email, messaging, support, or security provider is enabled by the deployment platform.
6. That the public Privacy Notice accurately identifies material third-party processing.
7. That only minimum necessary data is shared with each provider.

This register must be updated **before** enabling a new third-party processor, not after deployment.

## 6. Evidence references

The application code currently demonstrates the following relevant data flows:

- `app/services/storage_driver.py` performs private Supabase object operations server-side.
- `app/services/payment_gateway.py` creates Razorpay orders and verifies payment/webhook signatures server-side.
- `app/templates/public/checkout.html` sends only payment-required checkout prefill data to Razorpay Checkout.js.
- `app/extensions.py` and the Phase 23 rate-limiting implementation use shared Redis-compatible storage for production rate-limit state.
- `vercel.json` identifies Vercel as the deployment platform.

## 7. Phase 24 boundary

Phase 24 establishes the engineering register and minimum-data-sharing controls. Actual production provider identity/region, contractual execution, and live environment verification remain deployment evidence and are verified again in **PDP Phase 32 — Production Configuration Test**.
