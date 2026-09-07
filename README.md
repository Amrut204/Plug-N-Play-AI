<div align="center">

# ⚡ Plug-N-Play AI

### Developer-First AI Assistant for SQL Databases & Documents

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20+%20pgvector-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Docker](https://img.shields.io/badge/Docker-Compose%20Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](docker-compose.yml)
[![Groq LPU](https://img.shields.io/badge/Groq-LPU%20Inference-F55036?style=for-the-badge&logo=groq&logoColor=white)](https://groq.com/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <strong>Drop-in natural language search for Postgres, MySQL, Mongo & documents. Connect existing schemas directly, enforce read-only SQL safety with AST parsing, and embed a floating assistant into React, Next.js, or Vue in 2 minutes.</strong>
</p>

[Why Plug-N-Play?](#-why-plug-n-play-ai) •
[Key Capabilities](#-key-capabilities) •
[Architecture](#-system-architecture) •
[Quickstart](#-quickstart--local-setup) •
[Docker Deployment](#-production-deployment-docker--cloud) •
[Widget Integration](#-embeddable-widget-integration) •
[Security & Guardrails](#-read-only-safety--security-guardrails)

---

</div>

## 📌 Why Plug-N-Play AI?

Every web application has operational data in databases (like **PostgreSQL**, **MySQL**, or **MongoDB**) and policies in **PDFs or Markdown documents**. 

When building an AI search or conversational assistant over this data, developers typically face three bad options:
1. **Building Text-to-SQL from scratch**: Fragile prompt templates that hallucinate table names, fail on joins, or create catastrophic security vulnerabilities (`DROP TABLE`, prompt injections, data leaks).
2. **Heavy ETL into proprietary vector databases**: Moving relational data into external vector stores that duplicate databases, lose relational constraints, drift out of sync, and balloon monthly cloud bills.
3. **Complex multi-service pipelines**: Cobbling together separate LangChain wrappers, embedding servers, authentication layers, and custom chat UIs.

**Plug-N-Play AI is a developer-first, self-contained solution:**
- **Zero ETL / Zero Migration**: Connect directly to your existing database with a read-only user or paste your schema DDL.
- **Guaranteed Read-Only SQL**: Every synthesized query passes through an Abstract Syntax Tree (AST) validator (`sqlglot`) that strictly blocks any non-`SELECT` query before execution.
- **Hybrid Search Out of the Box**: Intelligently routes questions between Text-to-SQL (tabular data), dense Vector RAG (documents via local `pgvector`), or composite hybrid answers.
- **Turnkey Embeddable Widget**: A lightweight Vanilla JS client with pre-generated, copy-paste components for **React**, **Next.js**, **Vue**, **Angular**, and **Svelte** with auth-gating and route whitelisting.

---

## ✨ Key Capabilities

### 🗄️ 1. Multi-Source Agentic Query Routing & Composite Answers
- **Parallel Multi-Source Execution**: Decomposes user questions across configured data stores (**PostgreSQL**, **MySQL**, **MongoDB**, **SQLite**) and executes targeted sub-queries in parallel using `asyncio.gather`.
- **Contextual Key Joining**: Merges related records on matching keys (e.g., `user_id`, `customer_id`, `order_id`) in-memory to assemble a coherent answer (e.g., pulling a student's profile from Postgres and unpaid invoices from MySQL).
- **Graceful Degradation**: If one secondary source times out or is unreachable, the orchestrator answers from the available data sources rather than failing the entire request.
> *Scope Note: Designed for operational application assistants, internal dashboards, and customer support bots. For multi-terabyte analytical joins across data lakes, use dedicated OLAP engines like Trino or Snowflake.*

### 🛡️ 2. Zero-Knowledge Schema Bridge
- **Zero Credential Exposure**: Organizations with strict compliance or firewall constraints can provide plain SQL DDL or Prisma schemas without sharing live database connection strings or passwords.
- **Local VPC Execution**: Plug-N-Play AI generates AST-sanitized read-only SQL for your private backend (Node.js Express, Python FastAPI, Laravel PHP) to execute against your private database cluster. Only query results are passed back for natural language formatting.

### 🧠 3. Hybrid Routing (SQL + Dense Vector RAG)
- **Automatic Intent Classifier**: Routes user prompts to the best retrieval engine:
  - **SQL / MQL Engine**: Computes exact counts, averages, filters, and relational lookups.
  - **Vector RAG Engine**: Performs semantic search across uploaded PDF/DOCX/Markdown documents using dense cosine similarity on PostgreSQL `pgvector` (HNSW index).
  - **Composite Hybrid Engine**: Combines tabular facts and document guidelines into a unified, source-cited response.
- **Local FastEmbed Embeddings**: Uses ONNX Runtime (`BAAI/bge-small-en-v1.5`, 384 dimensions) locally. Embedding generation takes $< 8\text{ms}$ with zero OpenAI embedding API costs.

### 🔒 4. AST Guardrails & Row-Level Security
- **Strict AST Validation (`sqlglot`)**: Rejects any statement containing `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, or query-stacking semicolons (`;`).
- **Deterministic Gate 1 Intent Shield**: Sub-millisecond regex & pattern rules block prompt injections and jailbreaks in $< 2\text{ms}$ with **0 LLM tokens consumed**.
- **Row-Level Security (RLS) Identity Injection**: Automatically injects tenant and user constraints (e.g. `AND user_id = :auth_user_id`) into generated queries to prevent cross-tenant or horizontal data leaks.
- **Automated PII Scrubber**: Masks passwords, credit card patterns, social security numbers, and sensitive salary columns before passing data into LLM synthesis.

### ⚡ 5. Low-Latency Streaming Pipeline
- **Groq LPU Acceleration**: High-speed token generation at **$300\text{--}500+\text{ tokens/sec}$** using `llama-3.3-70b-versatile` with automated multi-key failover rotation.
- **Semantic Query Caching**: Upstash Redis cache resolves repeated or semantically identical questions in **$15\text{--}35\text{ms}$**.
- **Real-Time Token Streaming**: Server-Sent Events (SSE) deliver real-time token streaming with live query telemetry.

### 🎨 6. Multi-Framework Embeddable Widget
- **Zero NPM Dependencies**: Pure Vanilla JS widget (`pnp-widget.js`) with complete styling isolation.
- **Framework-Ready Components**: Visual studio generates ready-to-use snippets for:
  - **React** (TypeScript TSX & JavaScript JSX)
  - **Next.js** (App Router with `strategy="afterInteractive"`)
  - **Angular** (v16+ Standalone Components)
  - **Vue 3** (Composition API / Nuxt 3)
  - **Svelte / SvelteKit**
  - **Plain HTML / WordPress / Shopify / Webflow**
- **3 Deployment Modes**:
  - `🌐 All Pages`: Always visible for marketing and public knowledge bases.
  - `🔒 Logged-in Users Only`: Renders only when authenticated; unmounts immediately on logout to safeguard API quotas.
  - `📍 Selected Pages Only`: Whitelists specific route paths (e.g. `/support, /help, /checkout`) with optional auth-on-page guards.

---

## 🏗 System Architecture

```
                                  CLIENT APPLICATION & FRONTEND
                             ┌─────────────────────────────────────┐
                             │   Web/Mobile App    Private Backend │
                             │        │                  │         │
                             │  [Embed Widget]    [Bridge Router]  │
                             └────────┼──────────────────┼─────────┘
                                      │                  │
                          Short-Lived JWT Token     HMAC-SHA256
                                      │                  │
                                      ▼                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               PLUG-N-PLAY AI DATA PLATFORM                             │
│                                                                                        │
│  ┌─────────────────────────┐  ┌──────────────────────────┐  ┌───────────────────────┐  │
│  │   API Gateway & Auth    │  │  Multi-Tenant Isolation  │  │ Semantic Data Schema  │  │
│  │ (HMAC / JWT Validation) │  │  (Workspace Partition)   │  │   & DDL Dictionary    │  │
│  └────────────┬────────────┘  └──────────────────────────┘  └───────────────────────┘  │
│               │                                                                        │
│               ▼                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                      🛡️ GATE 1 FAST INTENT & SAFETY SHIELD                       │  │
│  │           (Sub-1ms Regex & Guardrail Intent Compiler — 0 LLM Tokens)             │  │
│  └────────────────────────────────────┬─────────────────────────────────────────────┘  │
│                                       │                                                │
│                                       ▼                                                │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                       INTELLIGENT DUAL-ENGINE ROUTER                             │  │
│  │             (Routes: SQL/MQL vs Vector RAG vs Composite Hybrid)                  │  │
│  └────────┬───────────────────────────────────┬─────────────────────────────────────┘  │
│           │                                   │                                        │
│           ▼                                   ▼                                        │
│  ┌─────────────────────────────────┐ ┌─────────────────────────────────┐               │
│  │     MULTI-SOURCE SQL ENGINE     │ │        VECTOR RAG ENGINE        │               │
│  │  • Text-to-SQL / Text-to-MQL    │ │  • FastEmbed ONNX (bge-small)   │               │
│  │  • AST sqlglot Sanitization     │ │  • PostgreSQL pgvector (HNSW)   │               │
│  │  • Multi-Source Parallel Query  │ │  • Role-Aware Document Slicing  │               │
│  │  • Parallel Execution (gather)  │ │  • Dense Cosine Similarity Match│               │
│  └────────────────┬────────────────┘ └────────────────┬────────────────┘               │
│                   │                                   │                                │
│                   └─────────────────┬─────────────────┘                                │
│                                     ▼                                                  │
│                     ┌───────────────────────────────┐                                  │
│                     │  Hybrid Context Synthesizer   │                                  │
│                     │      & Data Scrubber          │                                  │
│                     └───────────────┬───────────────┘                                  │
│                                     │                                                  │
│                                     ▼                                                  │
│                     ┌───────────────────────────────┐                                  │
│                     │    Groq LPU Streaming Core    │                                  │
│                     │    (500+ Tokens/sec, SSE)     │                                  │
│                     └───────────────┬───────────────┘                                  │
└─────────────────────────────────────┼──────────────────────────────────────────────────┘
                                      │ Real-Time Token Stream (SSE)
                                      ▼
                             End User / Embed Widget
```

---

## ⚡ Performance Budget

| Query Scenario | Time-to-First-Token (TTFT) | Total Generation | Processing Pipeline |
| :--- | :--- | :--- | :--- |
| **🚀 Semantic Cache Hit** | **$15\text{ms} - 35\text{ms}$** | **$35\text{ms}$** | Upstash Redis exact/semantic match. |
| **🛡️ Blocked / Malicious** | **$< 2\text{ms}$** | **$< 5\text{ms}$** | Deterministic Gate 1 intent shield (0 LLM tokens). |
| **📄 Unstructured RAG** | **$180\text{ms} - 280\text{ms}$** | **$450\text{ms} - 650\text{ms}$** | FastEmbed ONNX search + pgvector HNSW + Groq LPU. |
| **🗄️ Database Text-to-SQL** | **$250\text{ms} - 420\text{ms}$** | **$600\text{ms} - 800\text{ms}$** | AST generation + Read-only DB fetch + Groq stream. |
| **🌐 Multi-Source Query** | **$300\text{ms} - 480\text{ms}$** | **$700\text{ms} - 900\text{ms}$** | Parallel `asyncio.gather` across databases + contextual key merge. |
| **🔒 Zero-Knowledge Bridge** | **$350\text{ms} - 550\text{ms}$** | **$750\text{ms} - 950\text{ms}$** | Schema query generation $\rightarrow$ client local execution $\rightarrow$ answer synthesis. |

---

## 🛠 Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend Framework** | Python 3.11+, FastAPI, Pydantic v2, Uvicorn |
| **Database & Vector Store** | PostgreSQL 16 with `pgvector` (HNSW indexing), SQLAlchemy 2.0 (Async) |
| **Async DB Connectors** | `asyncpg` (PostgreSQL), `aiomysql` (MySQL), `motor` (MongoDB), `aiosqlite` (SQLite) |
| **Inference & Acceleration** | Groq LPU API (`llama-3.3-70b-versatile`, `mixtral-8x7b-32768`), OpenAI fallback |
| **Embedding Engine** | FastEmbed ONNX Runtime (`BAAI/bge-small-en-v1.5`, 384 dims, local execution) |
| **Cache & Rate Limiting** | Upstash Redis (Semantic Query Cache, Rate Limiting, Session State) |
| **Security & Parsing** | `sqlglot` (SQL AST Validation), `PyJWT` (RS256/HS256), `cryptography` (Fernet) |
| **Frontend & UI** | Vanilla HTML5 / CSS3 Design System, Vanilla JS Embeddable Widget (`pnp-widget.js`) |

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- Python 3.11 or higher
- PostgreSQL with `pgvector` extension (or local Docker container)
- Groq API Key (from [console.groq.com](https://console.groq.com))

### 2. Clone the Repository
```bash
git clone https://github.com/Amrut204/Plug-N-Play-AI.git
cd Plug-N-Play-AI
```

### 3. Create and Activate Virtual Environment
```bash
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On macOS / Linux:
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 5. Configure Environment Variables
Create a `.env` file in the project root:
```env
# Database (PostgreSQL with pgvector)
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/plugnplay

# Groq LPU Inference (Get a free key at console.groq.com)
GROQ_API_KEY=gsk_your_groq_api_key

# Optional: Failover Groq keys for automatic rate-limit rotation
GROQ_API_KEY_1=gsk_optional_key_1
GROQ_API_KEY_2=gsk_optional_key_2

# Redis Cache (Optional - Upstash Redis or local Redis)
REDIS_URL=redis://localhost:6379/0

# Platform Security & Authentication
SECRET_KEY=generate_a_random_32_byte_secret_key_here
ENVIRONMENT=development
```

### 6. Run the Application
```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

- **Agent Studio & Dashboard**: Open [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger API Docs**: Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 🐳 Production Deployment (Docker & Cloud)

### Option 1: Self-Hosted Docker Compose (Recommended)

The repository includes a ready-to-run [`docker-compose.yml`](docker-compose.yml) that starts PostgreSQL 16 with `pgvector`, Redis, and the optimized backend container:

```bash
# 1. Provide your Groq API key in .env:
echo "GROQ_API_KEY=gsk_your_key_here" >> .env

# 2. Launch the full stack in detached mode:
docker compose up -d

# 3. View live server logs:
docker compose logs -f backend
```

Services started:
- `pnp_postgres`: PostgreSQL 16 with `pgvector` pre-installed on port `5432`
- `pnp_redis`: Redis 7 Alpine on port `6379`
- `pnp_backend`: FastAPI container with non-root security and pre-warmed ONNX embeddings on port `8000`

### Option 2: Cloud Container Hosting (Railway, Render, AWS, GCP)

Deploy the pre-built container or use the included [`render.yaml`](render.yaml) blueprint:

1. Connect your repository in your cloud dashboard (Render, Railway, or Cloud Run).
2. Set the environment variables:
   - `DATABASE_URL`: Cloud PostgreSQL connection string (e.g. [Neon Serverless PostgreSQL](https://neon.tech))
   - `GROQ_API_KEY`: Groq LPU API key
   - `SECRET_KEY`: Cryptographically secure JWT secret key
3. Start command:
   ```bash
   python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT
   ```

> [!NOTE]
> **🧪 Evaluation & Sandbox Setup**:
> For testing and proof-of-concept evaluation, you can run this stack at zero infrastructure cost by combining free developer tiers (Neon PostgreSQL 0.5 GB, Groq Cloud free tier, and Upstash Redis).

---

## 🔌 Embeddable Widget Integration

Plug-N-Play AI provides ready-to-use, framework-specific components directly in Step 4 of the Agent Studio and via the Dashboard Quick Embed Modal.

### 1. Plain HTML / WordPress / Webflow (1-Step Embed)
Paste this script tag right before `</body>`:

```html
<script 
  src="https://your-domain.com/static/pnp-widget.js"
  data-api-host="https://your-domain.com"
  data-agent-id="YOUR_AGENT_ID"
  data-title="AI Assistant"
  data-primary-color="#6366f1"
  data-position="bottom-right"
  async>
</script>
```

### 2. React (TSX) Component
```tsx
import React, { useEffect } from 'react';

export function AIWidget({ userId = 'guest', userRole = 'user' }) {
  useEffect(() => {
    if (document.getElementById('pnp-widget-script')) return;

    const script = document.createElement('script');
    script.id = 'pnp-widget-script';
    script.src = 'https://your-domain.com/static/pnp-widget.js';
    script.setAttribute('data-api-host', 'https://your-domain.com');
    script.setAttribute('data-agent-id', 'YOUR_AGENT_ID');
    script.setAttribute('data-title', 'AI Assistant');
    script.setAttribute('data-user-id', userId);
    script.setAttribute('data-user-role', userRole);
    script.async = true;
    document.body.appendChild(script);

    return () => {
      document.getElementById('pnp-widget-script')?.remove();
      document.querySelectorAll('#pnp-widget-container, #pnp-widget-trigger').forEach(el => el.remove());
    };
  }, [userId, userRole]);

  return null;
}
```

#### Auth-Gated Deployment (Logged-in Users Only)
```tsx
import { AIWidget } from './components/AIWidget';
import { useAuth } from './context/AuthContext';

export function App() {
  const { user, isAuthenticated } = useAuth();

  return (
    <div>
      <main>{/* Your application */}</main>

      {/* 🔒 Only rendered when user is logged in; unmounts immediately on logout */}
      {isAuthenticated && (
        <AIWidget userId={user?.id} userRole={user?.role} />
      )}
    </div>
  );
}
```

### 3. Next.js (App Router)
```tsx
// app/layout.tsx
import Script from 'next/script';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        {children}
        <Script
          src="https://your-domain.com/static/pnp-widget.js"
          data-api-host="https://your-domain.com"
          data-agent-id="YOUR_AGENT_ID"
          strategy="afterInteractive"
        />
      </body>
    </html>
  );
}
```

---

## 🔒 Read-Only Safety & Security Guardrails

```
User Query ──> [Gate 1: Intent & Anti-Jailbreak Shield]
                 │ (< 2ms deterministic refusal for prompt injections)
                 ▼
               [AST Parser & sqlglot Sanitizer]
                 │ (STRICT: Rejects anything that is not a SELECT statement)
                 ▼
               [Row-Level Security (RLS) Identity Injection]
                 │ (Appends WHERE user_id = :auth_user_id automatically)
                 ▼
               [Post-Execution PII Scrubber]
                 │ (Masks passwords, credit card numbers, and restricted fields)
                 ▼
               [Sanitized Response Stream (SSE)]
```

1. **AST Query Sanitization**: The SQL generation engine validates queries against an Abstract Syntax Tree using `sqlglot`. Statements containing modification verbs (`UPDATE`, `DELETE`, `INSERT`, `DROP`, `ALTER`, `TRUNCATE`) or multiple semicolon-delimited commands are rejected before touching any database driver.
2. **Deterministic Gate 1 Shield**: Pre-compiled regex and rule matrices evaluate user intent in $< 2\text{ms}$ without consuming LLM inference tokens.
3. **Automated Row-Level Identity Binding**: Automatically injects tenant and authenticated user constraints (e.g. `AND user_id = :auth_user_id`) into generated SQL to prevent horizontal cross-user data leakage.
4. **Post-Execution Data Scrubber**: Automatically strips sensitive fields (e.g., hashed credentials, payment tokens) before feeding database results into the LLM synthesis context.

---

## 🧪 Testing & Verification

Run the automated test suites using `pytest`:

```bash
# Run RBAC identity and security query tests
pytest backend/tests/test_rbac_identity_queries.py -v

# Run multi-database connection tests
python backend/test_multi_db_setup.py

# Run zero-knowledge schema bridge tests
python backend/test_zk_multi_db.py

# Run end-to-end streaming multi-agent test
python backend/test_streaming_multiagent_feedback_e2e.py
```

---

## 📂 Repository Structure

```
Plug-N-Play-AI/
├── backend/
│   ├── app/
│   │   ├── api/v1/                # REST API routers (chat, agents, connections, auth)
│   │   ├── core/                  # Database engines, security, encryption, settings
│   │   ├── models/                # Multi-tenant SQLAlchemy ORM models
│   │   ├── schemas/               # Pydantic v2 request/response schemas
│   │   ├── services/
│   │   │   ├── connectors/        # Database drivers (Postgres, MySQL, Mongo, SQLite)
│   │   │   ├── sql/               # Text-to-SQL / Text-to-MQL engine & sqlglot AST validator
│   │   │   ├── rag/               # Chunking, FastEmbed ONNX embedder, pgvector search
│   │   │   ├── router/            # Intent classification & context re-writer
│   │   │   ├── hybrid/            # Multi-source agentic orchestrator & streaming engine
│   │   │   ├── guardrails/        # Gate 1 & 2 safety shields and intent compiler
│   │   │   ├── cache/             # Upstash Redis semantic cache
│   │   │   └── llm/               # Groq LPU & multi-key failover gateway
│   │   ├── static/                # Agent Studio dashboard, UI styles, & pnp-widget.js
│   │   └── main.py                # FastAPI app initialization, middleware, & routes
│   ├── tests/                     # Automated test suites
│   ├── Dockerfile                 # Production multi-stage Docker build
│   └── requirements.txt           # Python dependencies
├── examples/                      # Integration examples & sample schemas
├── docker-compose.yml             # 1-Command self-hosted stack (Postgres + Redis + API)
├── render.yaml                    # Cloud infrastructure blueprint
└── README.md                      # Platform documentation
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
Feel free to check the [issues page](https://github.com/Amrut204/Plug-N-Play-AI/issues).

1. Fork the repository
2. Create your branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.
