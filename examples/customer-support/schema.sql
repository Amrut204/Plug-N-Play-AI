-- =============================================================================
-- Customer Support, Helpdesk & Account Management Database Schema
-- Compatible with PostgreSQL and SQLite
-- =============================================================================

CREATE TABLE IF NOT EXISTS accounts (
    id VARCHAR(64) PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    support_tier VARCHAR(50) DEFAULT 'standard', -- standard, priority, dedicated
    health_score INTEGER DEFAULT 100,            -- 0 to 100
    account_manager VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contacts (
    id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) REFERENCES accounts(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    is_primary BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS support_agents (
    id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    tier_level VARCHAR(20) DEFAULT 'tier1', -- tier1, tier2, tier3, lead
    is_available BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS tickets (
    id VARCHAR(64) PRIMARY KEY,
    account_id VARCHAR(64) REFERENCES accounts(id),
    contact_id VARCHAR(64) REFERENCES contacts(id),
    assigned_agent_id VARCHAR(64) REFERENCES support_agents(id),
    ticket_number VARCHAR(50) UNIQUE NOT NULL,
    subject VARCHAR(255) NOT NULL,
    priority VARCHAR(20) DEFAULT 'medium', -- low, medium, high, urgent
    status VARCHAR(50) DEFAULT 'open',     -- open, in_progress, waiting_on_customer, resolved, closed
    channel VARCHAR(30) DEFAULT 'web',     -- web, email, chat, api
    sla_due_at TIMESTAMP,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ticket_messages (
    id VARCHAR(64) PRIMARY KEY,
    ticket_id VARCHAR(64) REFERENCES tickets(id),
    sender_type VARCHAR(20) NOT NULL, -- customer, agent, system
    sender_name VARCHAR(255) NOT NULL,
    message_body TEXT NOT NULL,
    is_internal_note BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed Data
INSERT INTO accounts (id, company_name, support_tier, health_score, account_manager) VALUES
('acc_01', 'Starlight Media', 'dedicated', 94, 'Jessica Alba'),
('acc_02', 'Vortex Robotics', 'priority', 82, 'David Chen'),
('acc_03', 'GreenSprout Organic', 'standard', 68, 'Jessica Alba');

INSERT INTO contacts (id, account_id, email, full_name, phone, is_primary) VALUES
('cnt_01', 'acc_01', 'elena.r@starlight.com', 'Elena Rostova', '+1-555-0101', TRUE),
('cnt_02', 'acc_02', 'kenji.s@vortex.jp', 'Kenji Sato', '+1-555-0102', TRUE),
('cnt_03', 'acc_03', 'maria.g@greensprout.com', 'Maria Garcia', '+1-555-0103', TRUE);

INSERT INTO support_agents (id, email, full_name, tier_level, is_available) VALUES
('agt_1', 'charlie.tech@support.com', 'Charlie Brooks', 'lead', TRUE),
('agt_2', 'dana.help@support.com', 'Dana Scully', 'tier2', TRUE),
('agt_3', 'sam.frontline@support.com', 'Sam Wilson', 'tier1', FALSE);

INSERT INTO tickets (id, account_id, contact_id, assigned_agent_id, ticket_number, subject, priority, status, channel) VALUES
('tkt_101', 'acc_01', 'cnt_01', 'agt_2', 'TCK-1001', 'Webhook payload delivery timeouts on invoice.paid', 'high', 'in_progress', 'web'),
('tkt_102', 'acc_02', 'cnt_02', 'agt_1', 'TCK-1002', 'Custom SAML SSO certificate rotation required', 'medium', 'open', 'email'),
('tkt_103', 'acc_03', 'cnt_03', 'agt_3', 'TCK-1003', 'How to add extra team member seats to billing', 'low', 'resolved', 'chat');

INSERT INTO ticket_messages (id, ticket_id, sender_type, sender_name, message_body, is_internal_note) VALUES
('msg_1', 'tkt_101', 'customer', 'Elena Rostova', 'We are observing 504 gateway timeouts when our webhook endpoint receives invoice events.', FALSE),
('msg_2', 'tkt_101', 'agent', 'Dana Scully', 'Investigating server response logs; retrying payload dispatch with backoff.', FALSE),
('msg_3', 'tkt_101', 'agent', 'Dana Scully', 'Note for Tier 3: Ingress controller latency spike during 04:00 UTC batch job.', TRUE),
('msg_4', 'tkt_102', 'customer', 'Kenji Sato', 'Our Okta signing certificate expires next Tuesday. Can you guide us through rotation?', FALSE);
