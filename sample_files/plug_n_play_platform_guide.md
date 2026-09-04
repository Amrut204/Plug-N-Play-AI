# Plug-N-Play AI — Complete Platform Knowledge Base & Architecture Guide

> **Document Version:** 2.4 | **Target:** Platform Assistant Agent, Client Developers, System Administrators  
> **Platform URL:** [https://plug-n-play-rag.onrender.com/](https://plug-n-play-rag.onrender.com/)

---

## 1. Executive Summary & Core Architectural Philosophy

**Plug-N-Play AI** is an enterprise-grade, zero-write AI data layer and autonomous agent orchestration platform. It empowers developers and enterprises to connect their private databases, unstructured documents, and web services to conversational AI agents and embed intelligent assistants directly into any website or application within minutes.

### Key Architectural Pillars
- **"Bring AI to your data, never your data to an external black box."**
- **Dual-Engine Architecture:** Combines unstructured document retrieval (RAG with vector embeddings) and live structured database querying (Text-to-SQL with AST validation).
- **Zero Database Write Mandate:** Non-negotiable read-only safety. All state-modifying SQL queries (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`) are intercepted and rejected at the AST level.
- **Cryptographic Multi-Tenant Isolation:** Workspaces are isolated by Tenant UUID and scoped schemas. Cross-tenant leakage is mathematically impossible.

---

## 2. Core Agent Types & Capabilities

| Agent Type | Engine | Supported Inputs | Primary Use Cases |
|---|---|---|---|
| **Knowledge Base (RAG)** | Vector Embeddings + Cosine Similarity | PDF, TXT, MD, CSV, JSON, DOCX | Support documentation, policy handbooks, FAQs, product catalogs |
| **Operational Database** | Text-to-SQL + AST Validator | SQLite, PostgreSQL, MySQL | Order lookups, student attendance, CRM inventory metrics |
| **Action & Browser Relay** | REST APIs + Webhooks + Ambient Relays | HTTP JSON endpoints, DOM Events | Cart operations, tab switching, ticket submissions, form prefill |

### A. Unstructured RAG Pipeline
1. **Document Ingestion:** Parses raw files, stripping formatting noise and binary headers.
2. **Semantic Chunking:** Generates overlapping semantic windows (default 500 characters, 100 character overlap) to preserve continuity.
3. **Vector Embeddings:** Creates high-dimensional embeddings for indexing.
4. **Hybrid Retrieval:** Calculates cosine similarity against incoming queries, retrieving the top-K relevant chunks to inject into the LLM system prompt.

### B. Operational Database (Text-to-SQL) & AST Security Engine
1. **Schema Introspection:** Reads database column names, data types, and relationships in read-only mode.
2. **Abstract Syntax Tree (AST) Validation:** Validates generated SQL through an AST parser. Destructive statements (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, semicolon chaining, comments, and file writes) are blocked instantly.
3. **Self-Healing Query Retries:** If SQL syntax errors or column mismatches occur, the engine captures the database dialect feedback and self-corrects up to 3 times before replying.

### C. Action Agents & Ambient Browser Relays
- **External Webhooks:** Dispatches authenticated HTTP requests to your backend endpoints.
- **Ambient Browser Relays:** Uses the user's active session cookies and CSRF tokens in their browser to perform client-side UI actions (e.g., navigating pages, adding items to cart) without exposing server API keys.

---

## 3. Client Testing Free Tier

Plug-N-Play AI offers an unrestricted **Client Testing (Free Tier)** for all registered workspaces:
- **Zero-Friction Access:** No credit card required.
- **Full Studio Features:** Create unlimited RAG, Text-to-SQL, and Action agents.
- **Universal Widget Deployment:** Embed on local development servers, staging environments, or production domains.
- **Real-Time Fleet Telemetry:** Access CSAT scores, query volume analytics, shield block metrics, and latency dashboards.

---

## 4. Web Application Integration Guide

Deploying an agent requires a single HTML script tag generated inside the **Agent Studio**.

### Universal Embed Code
```html
<script 
  src="https://plug-n-play-rag.onrender.com/static/widget.js" 
  data-agent-id="YOUR_AGENT_ID" 
  async>
</script>
```

### Framework Implementations
- **Vanilla HTML / WordPress:** Add inside `<head>` or before the closing `</body>` tag (e.g. in `footer.php`).
- **React (TSX / JSX):** Inject dynamically in `useEffect()` or add to `public/index.html`.
- **Next.js (App Router):** Use `<Script src="..." data-agent-id="..." strategy="afterInteractive" />`.
- **Angular:** Add script path to `angular.json` under `"scripts": []` or inject via `app.component.ts`.
- **Vue 3 / Nuxt 3:** Add in `App.vue` `onMounted()` or `nuxt.config.ts` in `app.head.scripts`.
- **Backend Bridges:** Direct API querying via `POST /api/v1/chat/query` using master API keys.

---

## 5. Security & Multi-Tenancy Safeguards

- **AST SQL Security Validator:** Strict `SELECT`-only execution.
- **Data Privacy:** Data is never sent to third-party public models for retraining.
- **HTTPS Port 443 Communications:** Eliminates firewall blocks for OAuth and email delivery.
- **Encrypted Credentials:** Passwords hashed with salted Bcrypt/Argon2; API keys hashed with SHA-256.

---

## 6. Human Escalation & Support Handover

When an agent encounters a query beyond its knowledge base or when a user requests human assistance:
1. The agent requests the visitor's contact information (email or phone).
2. An automated human escalation alert is generated via `EmailService`.
3. A styled HTML dispatch is routed to the client support email via HTTPS APIs (Resend, Brevo, SendGrid).
4. The alert includes the session ID, user query, conversation transcript, and a direct link to the Master Studio session.

---

## 7. Frequently Asked Questions (FAQ)

**Q: Can the agent modify or delete records in my database?**  
A: No. The platform enforces a strict Zero Database Write policy. Our AST SQL Validator rejects any `INSERT`, `UPDATE`, `DELETE`, `DROP`, or schema-altering query before execution.

**Q: What document types can I upload?**  
A: You can upload PDF (`.pdf`), plain text (`.txt`), Markdown (`.md`), CSV (`.csv`), JSON (`.json`), and Word (`.docx`) files.

**Q: How do I embed the agent on my website?**  
A: Copy your generated `<script>` tag from the Agent Studio and paste it before the closing `</body>` tag on any webpage.

**Q: How do I sign in or manage my account?**  
A: You can log in with 1-Click Google Sign-In or your email and password. In the top navigation bar, click your profile avatar to view your account details, click "Edit Profile" to modify your information, or click "Logout" to sign out.

**Q: Which LLM models power Plug-N-Play AI?**  
A: The platform runs high-speed inference on Groq hardware, supporting LLaMA 3.3 70B, Qwen 2.5 32B, DeepSeek R1 distillation, and OpenAI-compatible failover endpoints.
