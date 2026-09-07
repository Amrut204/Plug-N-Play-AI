# SaaS Product Terms, SLA & Operational Policies

## 1. Service Level Agreement (SLA) & Uptime Guarantee
- **Uptime Commitment**: We guarantee 99.95% monthly uptime across all core API endpoints, query services, and webhooks.
- **Scheduled Maintenance**: Maintenance windows occur on Sundays between 02:00 UTC and 04:00 UTC. Customers will receive at least 48 hours prior notice via status dashboard and email.
- **SLA Downtime Credits**:
  - Less than 99.95% but above 99.0%: 10% monthly subscription credit.
  - Less than 99.0% but above 95.0%: 25% monthly subscription credit.
  - Below 95.0%: 50% monthly subscription credit.
  - SLA credits must be requested within 30 days of the qualifying incident.

## 2. Plan Tiers & Resource Quotas
| Feature / Tier | Starter ($49/mo) | Growth ($199/mo) | Enterprise ($799/mo) |
| :--- | :--- | :--- | :--- |
| **User Seats** | Up to 5 seats | Up to 25 seats | Up to 100 seats (custom add-ons) |
| **Monthly API Queries** | 50,000 queries | 500,000 queries | 5,000,000 queries |
| **Burst Rate Limit** | 60 req/min | 600 req/min | 3,000 req/min |
| **Data Retention** | 30 days query logs | 90 days query logs | 365 days query logs |
| **Support Channel** | Email (48h response) | Slack + Email (12h response) | 24/7 Phone + Pager (1h response) |

## 3. Subscription & Billing Rules
- **Billing Cycles**: Subscriptions are billed either monthly or annually in advance. Annual subscriptions receive a 20% discount.
- **Overage Policy**: Excess API queries are billed at $10 per 50,000 additional queries at the end of the billing period.
- **Cancellation & Refunds**:
  - Monthly plans can be cancelled anytime with cancellation taking effect at the end of the active billing cycle.
  - Annual plans may be refunded on a pro-rata basis within 14 calendar days of initial purchase or renewal.
  - No refunds are issued for partially used months on monthly subscriptions.

## 4. Security & Data Isolation
- Each tenant's data is isolated logically by tenant identifier.
- Database credentials and secrets are encrypted with AES-256-GCM.
- Query executions are strictly read-only with mathematical AST validation preventing data mutation.
