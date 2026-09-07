-- =============================================================================
-- SaaS Operations & Billing Database Schema
-- Compatible with PostgreSQL and SQLite
-- =============================================================================

CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan_tier VARCHAR(50) DEFAULT 'starter', -- starter, growth, enterprise
    status VARCHAR(50) DEFAULT 'active',    -- active, past_due, cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) REFERENCES organizations(id),
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'member', -- owner, admin, member, billing_contact
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plans (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    monthly_price_cents INTEGER NOT NULL,
    max_seats INTEGER NOT NULL,
    included_api_calls INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) REFERENCES organizations(id),
    plan_id VARCHAR(64) REFERENCES plans(id),
    status VARCHAR(50) DEFAULT 'active', -- trialing, active, past_due, cancelled
    billing_cycle VARCHAR(20) DEFAULT 'monthly', -- monthly, annual
    mrr_cents INTEGER NOT NULL,
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS invoices (
    id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) REFERENCES organizations(id),
    subscription_id VARCHAR(64) REFERENCES subscriptions(id),
    amount_due_cents INTEGER NOT NULL,
    amount_paid_cents INTEGER DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'paid', -- draft, open, paid, void, uncollectible
    due_date TIMESTAMP,
    paid_at TIMESTAMP,
    invoice_pdf_url VARCHAR(512)
);

CREATE TABLE IF NOT EXISTS usage_metrics (
    id VARCHAR(64) PRIMARY KEY,
    org_id VARCHAR(64) REFERENCES organizations(id),
    metric_name VARCHAR(100) NOT NULL, -- api_calls, storage_bytes, active_seats
    metric_value BIGINT NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample Seed Data
INSERT INTO organizations (id, name, slug, plan_tier, status) VALUES
('org_001', 'Acme Logistics Inc', 'acme-logistics', 'growth', 'active'),
('org_002', 'CloudFlow Tech', 'cloudflow-tech', 'enterprise', 'active'),
('org_003', 'Nordic FinSoft', 'nordic-finsoft', 'starter', 'past_due');

INSERT INTO plans (id, name, monthly_price_cents, max_seats, included_api_calls) VALUES
('plan_starter', 'Starter', 4900, 5, 50000),
('plan_growth', 'Growth', 19900, 25, 500000),
('plan_enterprise', 'Enterprise', 79900, 100, 5000000);

INSERT INTO subscriptions (id, org_id, plan_id, status, billing_cycle, mrr_cents, current_period_start, current_period_end) VALUES
('sub_001', 'org_001', 'plan_growth', 'active', 'monthly', 19900, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('sub_002', 'org_002', 'plan_enterprise', 'active', 'annual', 63920, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('sub_003', 'org_003', 'plan_starter', 'past_due', 'monthly', 4900, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO users (id, org_id, email, full_name, role, is_active) VALUES
('usr_001', 'org_001', 'sarah.c@acme.com', 'Sarah Connor', 'owner', TRUE),
('usr_002', 'org_001', 'john.d@acme.com', 'John Doe', 'member', TRUE),
('usr_003', 'org_002', 'alex.w@cloudflow.io', 'Alex Wong', 'admin', TRUE),
('usr_004', 'org_003', 'erik.l@nordic.se', 'Erik Lindqvist', 'owner', TRUE);

INSERT INTO invoices (id, org_id, subscription_id, amount_due_cents, amount_paid_cents, status) VALUES
('inv_101', 'org_001', 'sub_001', 19900, 19900, 'paid'),
('inv_102', 'org_002', 'sub_002', 767040, 767040, 'paid'),
('inv_103', 'org_003', 'sub_003', 4900, 0, 'open');
