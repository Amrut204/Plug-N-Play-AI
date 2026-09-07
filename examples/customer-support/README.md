# Starter Template: Customer Support, Helpdesk & Account Management Assistant

Designed for Customer Success teams, technical support agents, and client-facing helpdesk portals.

## Components Included
1. **Relational Schema (`schema.sql`)**:
   - `accounts`: Company accounts, health scores (0–100), support tiers (`standard`, `priority`, `dedicated`), assigned account managers.
   - `contacts`: Primary customer stakeholders and contact info.
   - `support_agents`: Support tiers (`tier1`, `tier2`, `tier3`, `lead`) and availability status.
   - `tickets`: Ticket numbers, subjects, priorities (`low`, `medium`, `high`, `urgent`), statuses, channels (`web`, `email`, `chat`, `api`).
   - `ticket_messages`: Message thread, customer communications, and agent-only internal notes.
2. **Policy Documentation (`docs/knowledge_base_faq.md`)**:
   - P1 to P4 SLA response and resolution time windows.
   - SAML SSO certificate rotation instructions.
   - Webhook retry schedules, signature verification, and Dead Letter Queue (DLQ).
3. **Pre-configured Roles & RBAC**:
   - `lead` / `admin`: Full SLA breach monitoring, agent workload distribution, internal note visibility.
   - `support_rep`: Ticket triage, customer history, knowledge base synthesis.
   - `customer`: Programmatic RLS restricting queries to `WHERE account_id = :auth_account_id` and strictly suppressing internal notes (`is_internal_note = FALSE`).

## Quickstart Testing with SQLite
```bash
sqlite3 support_ops.db < examples/customer-support/schema.sql
```
Connect `sqlite:///support_ops.db` in the Agent Studio.
