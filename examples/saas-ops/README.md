# Starter Template: SaaS Internal Operations & Billing Assistant

This template sets up a dual-engine AI assistant for SaaS product teams, customer success leads, and finance managers.

## Components Included
1. **Relational Schema (`schema.sql`)**:
   - `organizations`: Account status, active tiers (`starter`, `growth`, `enterprise`).
   - `users`: Team members, administrative roles (`owner`, `admin`, `member`).
   - `plans` & `subscriptions`: Pricing, monthly recurring revenue (`mrr_cents`), billing cycles.
   - `invoices`: Due amounts, payment records, currency, status.
   - `usage_metrics`: API calls, storage usage, active seats.
2. **Policy Documentation (`docs/product_terms_sla.md`)**:
   - 99.95% SLA uptime tiers and credit refund calculations.
   - Plan rate limits and bursting limits.
   - Cancellation and refund policies.
3. **Pre-configured Roles & RBAC**:
   - `admin` / `owner`: Unrestricted aggregate reporting, ARR/MRR visibility, churn auditing.
   - `member`: Programmatic RLS constraining queries to `WHERE org_id = :auth_org_id`.

## Quickstart Testing with SQLite
```bash
sqlite3 saas_ops.db < examples/saas-ops/schema.sql
```
Then register `sqlite:///saas_ops.db` in the Plug-N-Play Agent Studio or upload the schema directly via the Zero-Knowledge Bridge.
