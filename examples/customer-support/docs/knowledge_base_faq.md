# Helpdesk Knowledge Base & Support Operations Guide

## 1. Ticket Priority & Response Time SLAs
- **Urgent (P1)**: Production outage, data loss risk. First response within **15 minutes**. Updates every 30 minutes.
- **High (P2)**: Core integration impaired, webhook delivery failure. First response within **1 hour**. Updates every 2 hours.
- **Medium (P3)**: Configuration issues, SSO certificate rotation. First response within **4 hours**.
- **Low (P4)**: General usage questions, billing seat adjustments. First response within **1 business day**.

## 2. Common Technical Workflows
### SAML / SSO Certificate Rotation
1. Navigate to **Settings > Security > Single Sign-On**.
2. Upload the new `.pem` public certificate provided by your Identity Provider (Okta, Azure AD, Google Workspace).
3. Do not delete the existing certificate until the test SAML assertion succeeds.
4. If an assertion error occurs, check that the clock skew between your IdP and our servers is within 180 seconds.

### Webhook Delivery & Retries
- Webhook payloads are signed using HMAC-SHA256 with your workspace webhook secret key (`X-Signature-256`).
- If an endpoint returns any HTTP code other than `2xx`, our dispatcher retries with exponential backoff: 1 minute, 5 minutes, 30 minutes, 2 hours, and 12 hours.
- Payloads that fail all retries are stored in the Dead Letter Queue (DLQ) for 14 days and can be manually re-dispatched via the dashboard.

## 3. Account Roles & Security Escalations
- Internal ticket notes (`is_internal_note = TRUE`) are strictly restricted to support agents and administrators. They must never be displayed to end-customers.
- To request an account manager reassignment, contact `accounts@plugnplay-ai.com` or ping your current account executive directly.
