# Third-Party Processor Register

Version: 1.0 | Review after every provider or integration change

| Processor / provider | Data shared | Purpose | Storage/location | Security / access | Retention |
|---|---|---|---|---|---|
| Supabase | Document objects and required metadata | Private document storage/database services | Provider-controlled infrastructure | Private bucket; server-side service-role credential; authorised application access | Per retention schedule |
| Razorpay | Payment/order information required to process donations | Payment processing and verification | Razorpay infrastructure | Server-side credentials; signature/webhook verification | Provider terms + applicable payment requirements |
| Vercel / hosting | Request and application data necessary to serve the application | Hosting/deployment | Hosting infrastructure | HTTPS, environment-managed secrets, restricted deployment access | Provider terms + operational requirements |
| Redis provider | Rate-limit keys and minimal throttling state | Shared production rate limiting | Provider infrastructure | No secrets or unnecessary personal content in keys | Short operational TTL |
| Email provider (if enabled) | Recipient address and message data necessary to send the message | Transactional communication | Provider infrastructure | Server-side credentials; minimum necessary data | Provider/operational schedule |
| Analytics/monitoring (if enabled) | Only data explicitly configured for measurement/diagnostics | Aggregate usage or security monitoring | Provider infrastructure | Must be reviewed for consent, minimisation and access controls | Defined analytics/log schedule |

## Governance

Before enabling a new provider, document the data fields shared, purpose, security controls, location, retention, contractual terms and lawful basis/justification. Do not enable analytics or optional communications merely because an SDK is available.
