# Plug-N-Play AI — Complete Platform Knowledge Base & Client Support Guide

> **Document Version:** 3.0  
> **Target Audience:** Platform Support AI Assistant, Client Onboarding, Technical Administrators, Integration Engineers  
> **Platform URL:** [https://plug-n-play-rag.onrender.com/](https://plug-n-play-rag.onrender.com/)  
> **Primary Use Case:** Training Platform Concierge Agents for 24/7 Client Question Answering & Troubleshooting

---

## Table of Contents
1. [Platform Overview & Core Architectural Philosophy](#1-platform-overview--core-architectural-philosophy)
2. [Agent Studio & Creation Wizard (Step-by-Step)](#2-agent-studio--creation-wizard-step-by-step)
3. [Deep-Dive: Database Integration & Multiple DB Connections](#3-deep-dive-database-integration--multiple-db-connections)
   - [Why is there another Database URL option? (Multi-DB Federation)](#a-why-is-there-another-database-url-option-multi-db-federation)
   - [What if I only have one database?](#b-what-if-i-only-have-one-database)
   - [Direct Cloud Connect vs. Zero-Knowledge Schema Mode](#c-direct-cloud-connect-vs-zero-knowledge-schema-mode)
   - [Supported Database Engines & URL Formats](#d-supported-database-engines--url-formats)
   - [AST SQL Syntax Safety & Read-Only Guarantee](#e-ast-sql-syntax-safety--read-only-guarantee)
4. [Deep-Dive: Knowledge Base Ingestion (Unstructured RAG)](#4-deep-dive-knowledge-base-ingestion-unstructured-rag)
5. [Deep-Dive: Action Agents & Ambient Browser Relays](#5-deep-dive-action-agents--ambient-browser-relays)
6. [Deep-Dive: Audience Guardrails & Row-Level Privacy](#6-deep-dive-audience-guardrails--row-level-privacy)
7. [Deep-Dive: Live Human Escalation & Support Handover](#7-deep-dive-live-human-escalation--support-handover)
8. [Universal Widget Embed & Framework Integration Guide](#8-universal-widget-embed--framework-integration-guide)
9. [Workspace Dashboard, Telemetry & Free Testing Tier](#9-workspace-dashboard-telemetry--free-testing-tier)
10. [Exhaustive Client FAQ & Troubleshooting Directory](#10-exhaustive-client-faq--troubleshooting-directory)

---

## 1. Platform Overview & Core Architectural Philosophy

**Plug-N-Play AI** is an enterprise-grade AI data layer and autonomous agent orchestration platform. It enables businesses, developers, universities, and organizations to connect their private databases, unstructured documents, and web services to conversational AI assistants and deploy embeddable widgets onto any website or web application in under five minutes.

### Core Architectural Pillars
1. **"Bring AI to your data, never your data to an external black box"**:
   - You do not need to export, migrate, or restructure your existing databases. Plug-N-Play AI bridges directly to your existing systems.
2. **Dual-Engine Retrieval (Unstructured RAG + Structured Text-to-SQL)**:
   - Typical chatbots only perform document search (RAG) and cannot query live relational databases. Plug-N-Play AI unifies both: an agent can look up policies in a PDF and query live order status in PostgreSQL in the exact same conversational turn.
3. **Non-Negotiable Zero Database Write Mandate**:
   - The platform never modifies, updates, inserts, or deletes records. Destructive queries are mathematically blocked at the Abstract Syntax Tree (AST) level before touching your database.
4. **Cryptographic Multi-Tenant Isolation**:
   - Every workspace is isolated by a unique Tenant UUID. No tenant can ever access, search, or view another tenant's documents, databases, vector embeddings, or chat histories.

---

## 2. Agent Studio & Creation Wizard (Step-by-Step)

The Agent Studio guides you through creating an autonomous AI agent in 4 simple steps:

### Step 1: Agent Identity & Role
- **Agent Name**: The display name visible to your visitors in the widget header (e.g., *"Acme Store Concierge"*, *"Campus Academic Advisor"*, *"Plug-N-Play Platform Guide"*).
- **Primary Role / Persona**: Defines the tone, identity, and behavioral boundaries of the bot (e.g., Customer Support, Technical Documentation Specialist, Sales Representative).
- **System Prompt**: Custom behavioral instructions tailored to your brand voice and communication style.

### Step 2: Knowledge Ingestion & Data Sources
- **Knowledge Base Documents (RAG)**: Upload PDFs, Markdown, TXT, Word, or CSV files for semantic vector search. You can also click 1-click preset chips (e.g., *SaaS SLA*, *E-Commerce*, *Plug-N-Play AI Guide*) to auto-populate the knowledge base.
- **Operational Database (SQL / NoSQL)**: Connect live databases via connection strings or paste SQL DDL schemas for real-time Text-to-SQL queries.

### Step 3: Audience Guardrails & Permissions
- Select your target audience boundary preset:
  - **End-User / Customer**: Strict Row Isolation (`WHERE user_id = :id`). Prevents exposing other users' private records, orders, or grades.
  - **Internal Staff / Support**: Team-level query access with sensitive column masking.
  - **Executive / Admin**: High-level cross-departmental reporting and aggregate metrics.
  - **Adaptive RBAC**: Dynamically switches permissions based on visitor JWT tokens.

### Step 4: Live Human Escalation & Actions
- Configure alert channels (**Direct Email**, **Slack/Discord Webhooks**, or **In-Widget Contact Cards**) to notify human team members when a user requests live support.
- Configure Action Webhooks or Ambient Browser Relays for automated task execution.
- Copy your 1-line embed snippet or test the bot instantly in the interactive preview sandbox.

---

## 3. Deep-Dive: Database Integration & Multiple DB Connections

### A. Why is there another Database URL option? (Multi-DB Federation)

In modern enterprise architectures, organizations rarely keep all their data in a single monolithic database. Plug-N-Play AI supports **Multi-Database Federation** out of the box by providing the option to add multiple database connection cards (e.g., Database #1, Database #2, etc.).

#### Why Clients Use Multiple Database Cards:
1. **Cross-Domain Data Federation**:
   - **E-Commerce Example**:
     - *Database #1 (PostgreSQL)*: Contains `orders`, `customers`, and `shipping_tracking`.
     - *Database #2 (MySQL)*: Contains `inventory_catalog`, `warehouse_stock`, and `suppliers`.
     - *Agent Capability*: A customer can ask: *"Is my order #4012 delayed due to warehouse stock?"* The agent queries Database #1 for the order items and Database #2 for warehouse status, returning a unified response in a single conversational turn.
2. **University & Higher Education Administration**:
   - *Database #1*: Student Information System (SIS) for course enrollments, GPA, and attendance.
   - *Database #2*: Bursar & Finance DB for tuition fees, scholarships, and outstanding dues.
3. **Microservices Architecture**:
   - Organizations frequently decouple authentication/users from transactional billing or product services. Connecting both databases gives the AI holistic context without requiring backend code changes.
4. **Read-Replica & Analytics Splitting**:
   - Point high-volume analytical queries to an AWS Aurora or Supabase read replica while keeping transactional customer queries on a primary database.

---

### B. What if I only have one database?

If your application only uses a single database, **you simply configure Database #1 and leave or delete the second database card**. 

The "+ Add Another Database" option is completely optional. The platform does not require multiple databases—it provides the capability so growing companies and enterprises never hit an architectural ceiling.

---

### C. Direct Cloud Connect vs. Zero-Knowledge Schema Mode

Plug-N-Play AI offers two distinct connection architectures depending on your organization's security posture:

| Feature | Direct Cloud Connect (Default) | Zero-Knowledge Schema Only Mode |
|---|---|---|
| **Credentials Required** | Connection String (URL) | **NONE** (No URL, No Password) |
| **How It Works** | Platform connects via SSL to execute real-time `SELECT` queries | You paste your SQL DDL / Prisma schema; AI outputs SQL for your backend to run |
| **Execution Location** | Cloud Connector over SSL | Behind your local corporate firewall |
| **Best For** | Cloud DBs (Neon, Supabase, AWS RDS, Render, DigitalOcean) | Banks, healthcare providers, on-premise VPCs, air-gapped networks |
| **Setup Time** | Under 1 minute | Under 3 minutes |

#### Security Recommendation for Direct Cloud Connect:
Create a dedicated read-only database user with limited privileges:
```sql
CREATE USER pnp_readonly WITH PASSWORD 'secure_password_here';
GRANT CONNECT ON DATABASE my_database TO pnp_readonly;
GRANT USAGE ON SCHEMA public TO pnp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO pnp_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO pnp_readonly;
```

---

### D. Supported Database Engines & URL Formats

Plug-N-Play AI automatically parses, validates, and normalizes all industry-standard database connection strings:

1. **PostgreSQL**:
   - Standard: `postgresql://user:password@host:port/dbname?sslmode=require`
   - SQLAlchemy / Neon async format: `postgresql+asyncpg://user:password@host:port/dbname?ssl=require`
   - Supabase / AWS RDS: Supports pooled (`port 6543`) and direct (`port 5432`) connections with SSL.
2. **MySQL & MariaDB**:
   - Standard: `mysql://user:password@host:3306/dbname`
   - Async formats: `mysql+aiomysql://...`, `mysql+pymysql://...`
3. **MongoDB (NoSQL)**:
   - Standard: `mongodb://user:password@host:27017/dbname`
   - Cloud Atlas SRV: `mongodb+srv://user:password@cluster.mongodb.net/dbname`
   - Translated into secure aggregation pipelines with automatic `$limit` protections.
4. **SQLite (Local Testing)**:
   - `sqlite:///path/to/database.db`

> **Note on Serverless Cold Starts (Neon, Supabase):**  
> Serverless databases spin down when idle. When the AI executes a query against a sleeping instance, the connection may take 2–4 seconds to establish. Plug-N-Play AI's connector engine includes built-in retry mechanisms and extended timeouts (7.0s) specifically optimized for serverless cloud databases.

---

### E. AST SQL Syntax Safety & Read-Only Guarantee

**Can a user or prompt injection attack trick the AI into dropping or modifying your database?**  
**ABSOLUTELY NOT.** Plug-N-Play AI enforces an **Abstract Syntax Tree (AST) Security Gate**:

- **AST Validation**: Before any generated SQL query is dispatched to your database, it is parsed into an abstract syntax tree and validated against strict whitelists.
- **Whitelist Only**: Only pure `SELECT` queries are permitted.
- **Destructive Keyword Rejection**: Any query containing `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`, or `EXEC` is rejected immediately, and a security shield alert is logged.
- **Semicolon Multi-Statement Blocking**: Attackers cannot chain statements with semicolons (e.g., appending destructive drops or updates). Multi-statement executions are blocked at the parser level.
- **Comment Stripping**: SQL comment syntax (`--`, `/* */`) commonly used in SQL injection is blocked.
- **Sensitive Column Masking**: Password hashes, salt tokens, CVV numbers, and private keys are filtered out of LLM contexts automatically.
- **Self-Healing Retries**: If the LLM produces a syntax error or references a misspelled column, the engine captures the database feedback and self-corrects up to 3 times before responding.

---

## 4. Deep-Dive: Knowledge Base Ingestion (Unstructured RAG)

The Knowledge Base allows agents to read unstructured company documents to answer visitor inquiries with pinpoint precision.

- **Supported File Types**: PDF (`.pdf`), Plain Text (`.txt`), Markdown (`.md`), CSV (`.csv`), JSON (`.json`), Microsoft Word (`.docx`), and Excel (`.xlsx`, `.xls`).
- **Ingestion Pipeline**:
  1. *Document Parsing*: Strips binary headers and extracts clean text and tabular records.
  2. *Overlapping Semantic Windows*: Splits documents into 500-character chunks with a 100-character overlap, ensuring semantic context is never lost across sentence boundaries.
  3. *High-Dimensional Vector Embeddings*: Embedded using 384-dimensional dense vectors.
  4. *Hybrid Cosine Retrieval*: Compares visitor queries against vector embeddings, retrieving the top most relevant passages and injecting them into the prompt.
- **Anti-Hallucination Scope Handling**:
  If a visitor asks about something not contained in the knowledge base, the agent does **NOT** guess, apologize, or hallucinate facts. It strictly states:
  > *"I don't have that information on file currently. Please click 'Support' below to connect with our team."*

---

## 5. Deep-Dive: Action Agents & Ambient Browser Relays

Unlike passive chatbots that can only converse, Plug-N-Play AI agents can **execute actions** directly on your website or web application.

### 1. Ambient Browser Relays
- **What it is**: The agent executes client-side actions directly inside the visitor's browser session.
- **Examples**:
  - Adding a recommended item to an e-commerce shopping cart.
  - Navigating the user to a checkout or appointment booking page.
  - Opening a specific settings modal or pre-filling an application form.
- **Security Advantage**: Relays execute using the visitor's existing session cookies and CSRF tokens in their browser. **You never need to expose server-side master API keys or administrative secrets to the AI.**

### 2. External API Webhook Triggers
- The agent can dispatch authenticated HTTP `POST` or `GET` webhooks to your backend when customer intents are met (e.g., creating a ticket in Zendesk, updating a CRM lead, or scheduling a consultation).

---

## 6. Deep-Dive: Audience Guardrails & Row-Level Privacy

In Step 3 of the Agent Studio, you configure Audience Boundary Presets to control data visibility:

1. **End-User / Customer (Strict Row Isolation)**:
   - Automatically appends `WHERE user_id = :authenticated_user_id` to all database queries.
   - Prevents one customer from ever seeing another customer's order history, personal address, grades, or private account data.
2. **Internal Staff / Customer Support**:
   - Permits broad operational lookups while masking confidential columns (like encrypted passwords and billing CVV codes).
3. **Executive / Management**:
   - Allows aggregate business queries (e.g., *"What was our total gross revenue this week?"*).
4. **Adaptive RBAC**:
   - Dynamically checks the visitor's JWT token role and adjusts table permissions in real time.

---

## 7. Deep-Dive: Live Human Escalation & Support Handover

When an AI agent cannot resolve a query or when a customer explicitly requests a human representative:

### 1. Automated Detection
- Triggered when a visitor says *"I want to talk to an agent"*, *"Help me with a human"*, or clicks the in-widget **"Support"** button.

### 2. Configurable Escalation Channels (Step 4)
- **Direct Email Alert**: Dispatches a formatted HTML alert via secure HTTPS APIs (Resend, Brevo, SendGrid) to your support email address.
- **Slack / Discord Webhooks**: Pushes an instant notification into your team's designated Slack or Discord channel.
- **In-Widget Contact Card**: Displays your support phone number, direct email, or booking link directly inside the widget.

### 3. Escalation Payload Delivered to Your Team
- Visitor contact info (email or phone).
- The exact query that triggered escalation.
- Full conversation transcript summary.
- Direct link to the live session in the Workspace Studio.

---

## 8. Universal Widget Embed & Framework Integration Guide

Deploying an agent to any website requires a single HTML `<script>` tag.

### Universal Embed Code Snippet
```html
<script 
  src="https://plug-n-play-rag.onrender.com/static/widget.js" 
  data-agent-id="YOUR_AGENT_ID" 
  async>
</script>
```

### Framework Implementations

#### 1. Plain HTML, WordPress & Shopify
Paste the script snippet immediately before the closing `</body>` tag (e.g., in WordPress `footer.php` or Shopify `theme.liquid`).

#### 2. React (TSX / JSX)
Place in `public/index.html` or inject dynamically in a root component:
```tsx
import { useEffect } from 'react';

export default function App() {
  useEffect(() => {
    const script = document.createElement('script');
    script.src = "https://plug-n-play-rag.onrender.com/static/widget.js";
    script.setAttribute('data-agent-id', 'YOUR_AGENT_ID');
    script.async = true;
    document.body.appendChild(script);
  }, []);

  return <div>Your Application</div>;
}
```

#### 3. Next.js (App Router & Pages Router)
```tsx
import Script from 'next/script';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        {children}
        <Script 
          src="https://plug-n-play-rag.onrender.com/static/widget.js" 
          data-agent-id="YOUR_AGENT_ID" 
          strategy="afterInteractive" 
        />
      </body>
    </html>
  );
}
```

#### 4. Angular
Add the script path to `angular.json` under `"scripts": []` or inject dynamically in `app.component.ts`.

#### 5. Vue 3 & Nuxt 3
- **Vue 3**: Add inside `onMounted()` in `App.vue`.
- **Nuxt 3**: Add to `app.head.scripts` inside `nuxt.config.ts`.

#### 6. Programmatic Server-to-Server REST API
You can query agents directly from backend services:
- **Endpoint**: `POST https://plug-n-play-rag.onrender.com/api/v1/chat/query`
- **Headers**:
  ```http
  Content-Type: application/json
  Authorization: Bearer YOUR_MASTER_API_KEY
  ```
- **Body**:
  ```json
  {
    "agent_id": "YOUR_AGENT_ID",
    "query": "What is our refund window?"
  }
  ```

### Widget Customization Attributes
| Attribute | Allowed Values | Description |
|---|---|---|
| `data-theme` | `"dark"` \| `"light"` | Forces dark mode or light mode |
| `data-accent` | Hex Color (e.g., `"#38bdf8"`) | Brand theme accent color |
| `data-position` | `"bottom-right"` \| `"bottom-left"` | Widget bubble placement |
| `data-user-id` | String (e.g., `"CUST_99182"`) | Authenticated visitor ID for row isolation |
| `data-user-role` | String (e.g., `"faculty"`) | Visitor role for role-based access control |

---

## 9. Workspace Dashboard, Telemetry & Free Testing Tier

1. **Client Testing (Free Tier)**:
   - Every registered workspace receives unrestricted access for testing and integrating AI agents on live websites.
   - Includes full Agent Studio features, RAG document parsing, direct database querying, and unlimited widget embeds.
2. **Real-Time Fleet Telemetry**:
   - The Workspace Dashboard displays live operational metrics:
     - **Configured Bot Fleet**: View, edit, and monitor all active agents.
     - **Total Queries Processed**: Track monthly customer query volume.
     - **User CSAT Score**: Aggregated thumbs up / thumbs down visitor feedback.
     - **Shield Blocks**: Tracks prevented SQL injection attempts and restricted column access attempts.
3. **Account Center & Security**:
   - Clicking your profile avatar opens the Account Center in **read-only mode**.
   - Click **"Edit Profile"** to modify your Full Name or Company Name.
   - Click **"Logout"** in the top navigation header or modal footer to securely terminate sessions.

---

## 10. Exhaustive Client FAQ & Troubleshooting Directory

### Q: What is the purpose of the "+ Add Another Database" option?
**A:** It enables **Multi-Database Federation**. Modern businesses frequently store customer orders in one database (e.g., PostgreSQL) and warehouse inventory in another (e.g., MySQL). Adding multiple databases allows your AI agent to query across both databases simultaneously in a single conversational turn. If you only have one database, you simply fill in Database #1 and ignore the extra card.

---

### Q: What if I only have one database? Do I need to fill in both?
**A:** No. If you have only one database, configure Database #1. The second database card is completely optional.

---

### Q: Can I connect different database engines at the same time?
**A:** Yes! For example, Database #1 can be PostgreSQL and Database #2 can be MySQL or MongoDB. The AI's dual-engine orchestrator parses table schemas from each connection and generates the appropriate dialect automatically.

---

### Q: How does the AI agent know which database to query?
**A:** During ingestion, the platform introspects the table schemas of all connected databases. When a visitor asks a question, the orchestrator inspects which tables contain the relevant attributes (e.g., orders vs. inventory) and dispatches queries to the appropriate database.

---

### Q: What is the difference between Direct Cloud Connect and Zero-Knowledge Schema Mode?
**A:** 
- **Direct Cloud Connect**: The platform connects directly to your cloud database over an encrypted SSL connection to execute real-time `SELECT` queries.
- **Zero-Knowledge Schema Mode**: For organizations with strict compliance or on-premise firewalls that cannot share credentials. You only provide your table schema (DDL), and the AI outputs the exact SQL for your local backend to run behind your private firewall.

---

### Q: Can the AI agent delete, update, or drop tables in my database?
**A:** No. The platform enforces a strict Zero Database Write policy. Our Abstract Syntax Tree (AST) validator intercepts and rejects any `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, semicolon chaining, or destructive command before execution. Only safe `SELECT` queries are executed.

---

### Q: What connection strings are supported for PostgreSQL?
**A:** Both standard PostgreSQL DSNs (`postgresql://user:pass@host:port/db?sslmode=require`) and SQLAlchemy / Neon async URLs (`postgresql+asyncpg://user:pass@host:port/db?ssl=require`). The platform automatically normalizes them.

---

### Q: Why do I experience a 2–4 second delay when testing a Neon database?
**A:** Serverless databases like Neon spin down to sleep when idle. When the AI sends a query, the database takes 2–4 seconds to cold-start. Our connector includes automatic retries and extended timeouts (7.0s) to handle serverless cold starts seamlessly.

---

### Q: What should I enter in the "Live Human Escalation" email section?
**A:** Enter your team's support email address (e.g., `support@yourcompany.com`). When a customer requests human assistance or clicks the "Support" button, a detailed summary and conversation transcript are emailed to that address immediately.

---

### Q: Why did my agent say: "I don't have that information on file currently"?
**A:** Plug-N-Play AI features strict anti-hallucination guardrails. If a query cannot be answered using your uploaded documents or connected databases, the agent will refuse to fabricate facts. To teach the agent new information, upload the document (or click a preset chip) in Step 2 of the Agent Studio and click "Save & Deploy".

---

### Q: Can I embed the chatbot on WordPress or Shopify?
**A:** Yes! Copy the `<script>` tag from the Agent Studio and paste it before the closing `</body>` tag in your WordPress `footer.php` or Shopify `theme.liquid`. The widget appears instantly.

---

### Q: Can the agent execute actions like adding items to a shopping cart?
**A:** Yes! Using Ambient Browser Relays, the agent can trigger client-side actions directly inside the visitor's browser session using their existing cookies and CSRF tokens without exposing server secrets.

---

### Q: Which LLM models power the platform?
**A:** Ultra-fast inference is provided by Groq hardware, supporting LLaMA 3.3 70B, Qwen 2.5 32B, DeepSeek R1 distillation, and OpenAI-compatible endpoints with automatic high-availability failover.

---

### Q: Is my company's proprietary data used to train public AI models?
**A:** Never. All customer data, documents, and vector embeddings are cryptographically segregated by Tenant ID and never sent to third-party public models for retraining.

---

### Q: How do I edit my profile or log out?
**A:** In the top navigation bar, click your profile avatar to view your account details in read-only mode. Click "Edit Profile" to modify your name or company, or click "Logout" in the top bar or modal footer to sign out securely.

---

### Q: Is the platform free for client testing and integration?
**A:** Yes. Every workspace has access to the Client Testing Free Tier, which includes full Agent Studio capabilities, RAG document ingestion, direct database querying, and unlimited widget embeds.

---

### Q: What is our workspace name or company name?
**A:** Our platform and company name is **Plug-N-Play AI** ([https://plug-n-play-rag.onrender.com/](https://plug-n-play-rag.onrender.com/)). If you are interacting with a custom agent created for your business, your workspace name is the project or company name specified during setup in the Agent Studio. You can view or update your company and workspace details at any time in the Account Center by clicking your profile avatar in the navigation bar.

