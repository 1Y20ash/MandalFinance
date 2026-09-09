# Data Breach Response Procedure

## Lifecycle

`DETECT → INVESTIGATE → CONTAIN → ASSESS → IDENTIFY AFFECTED DATA → DOCUMENT → NOTIFY WHERE REQUIRED → REMEDIATE → REVIEW`

## Detect

Treat suspected credential exposure, unauthorised document access, database compromise, payment/webhook tampering and accidental personal-data disclosure as security incidents.

## Investigate

Use application audit records, security logs, deployment logs and provider records. Avoid copying sensitive personal data into incident notes when an identifier or hash is sufficient.

## Contain

Revoke affected sessions/credentials, disable compromised accounts or integrations, restrict affected storage and isolate vulnerable functionality.

## Assess

Determine what personal data was affected, whose data was affected, whether confidentiality/integrity/availability was impacted, and whether notification obligations are triggered.

## Notify

The designated privacy/security owner determines and coordinates notifications required by applicable law, contractual commitments and provider procedures. Notification decisions and dates must be documented.

## Remediate and review

Patch the root cause, rotate affected secrets, verify restored controls, add regression tests and conduct a post-incident review.
