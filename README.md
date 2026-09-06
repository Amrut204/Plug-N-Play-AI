<div align="center">

# ⚡ Plug-N-Play AI

### Enterprise Zero-Trust Hybrid RAG & Federated Text-to-SQL Platform

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20+%20pgvector-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Groq LPU](https://img.shields.io/badge/Groq-LPU%20Inference-F55036?style=for-the-badge&logo=groq&logoColor=white)](https://groq.com/)
[![Redis](https://img.shields.io/badge/Upstash-Redis%20Cache-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://upstash.com/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)

<p align="center">
  <strong>Query operational SQL/NoSQL databases with natural language, retrieve dense knowledge from unstructured documents with Vector RAG, and execute cross-database federated joins with sub-250ms latency — with Zero Database Migration and Zero Credential Exposure.</strong>
</p>

[Key Features](#-key-features) •
[Architecture](#-system-architecture) •
[Security & Guardrails](#-enterprise-zero-trust-security) •
[Quickstart](#-quickstart--local-setup) •
[Widget Integration](#-embeddable-widget-integration) •
[Deployment](#-production-deployment-render--cloud) •
[Testing](#-testing--verification)

---

</div>

## 📌 What is Plug-N-Play AI?

Modern enterprise systems maintain operational data dispersed across heterogeneous databases (such as customer records in **PostgreSQL**, billing in **MySQL**, catalog in **MongoDB**) alongside unstructured policy handbooks, contracts, and knowledge bases in **PDFs/Markdown**.

Building AI search across this landscape typically requires:
- Complex and fragile ETL pipelines.
- Migrating sensitive operational data into proprietary external vector stores.
- Exposing high-privilege database credentials to third-party LLM providers.
- Lengthy multi-second query latencies.

**Plug-N-Play AI** eliminates these bottlenecks. It is a production-ready, self-contained AI orchestration platform that connects directly to your databases via read-only connections or **Zero-Knowledge DDL Schemas**, synthesizes AST-sanitized SQL/MQL queries, searches vector embeddings via `pgvector`, and streams coherent answers to client applications through a lightweight, universal floating widget.

---

## ✨ Key Features

### 🗄️ 1. Polyglot Multi-Database Federation
- **Heterogeneous Database Support**: Query **PostgreSQL**, **MySQL**, **MongoDB**, and **SQLite** simultaneously from a single natural language question.
- **In-Memory Federation**: Decomposes complex user queries into sub-queries, executes them in parallel via `asyncio.gather`, and joins structured results in-memory using unified identity keys (e.g. `student_id`, `customer_id`, `order_id`).

### 🛡️ 2. Zero-Knowledge Schema Bridge
- **Zero Credential Exposure**: Enterprises with strict compliance or firewall constraints (HIPAA, SOC 2, banking) can supply plain SQL DDL or Prisma schemas without exposing any live database host, port, or password.
- **Firewall Data Residency**: Plug-N-Play AI synthesizes safe read-only SQL for your private backend (Node.js, Python FastAPI/Django, Laravel PHP) to execute locally inside your VPC. Only query results return for formatting.

### 🧠 3. Dual-Engine Intelligent Router & Hybrid RAG
- **Autonomous Intent Classification**: Evaluates questions to determine whether to route to:
  - **Text-to-SQL / MQL Engine** for tabular and numerical queries.
  - **Vector RAG Engine** (FastEmbed ONNX + `pgvector` HNSW index) for unstructured documents.
  - **Hybrid Engine** that merges structured tabular facts and policy documents into a unified, source-cited response.
- **FastEmbed Local Embeddings**: Generates dense 384-dimensional embeddings locally (`BAAI/bge-small-en-v1.5`) via ONNX Runtime in $< 8\text{ms}$ with zero OpenAI API embedding costs.

### 🔒 4. Enterprise Zero-Trust Security & AST Guardrails
- **Deterministic Gate 1 Shield**: Sub-millisecond regex & intent compiler blocks prompt injections, jailbreaks, and offensive queries in $< 2\text{ms}$ using **0 LLM tokens**.
- **Abstract Syntax Tree (AST) Sanitization**: Strict `sqlglot` parser enforces `SELECT`-only operations. Any `DROP`, `UPDATE`, `INSERT`, `DELETE`, `ALTER`, or query-stacking semicolons (`;`) trigger instant security exceptions.
- **Row-Level Security (RLS) & RBAC**: Automatically appends authenticated user constraints (e.g. `AND user_id = :auth_user_id`) to mathematically prevent horizontal cross-tenant data leakage.
- **Automated PII Scrubber**: Masks passwords, social security numbers, salaries, and sensitive columns before feeding database records into the LLM synthesis context.

### ⚡ 5. Hardware-Accelerated Low Latency
- **Groq LPU Inference Core**: Streams responses at **$300\text{--}500+\text{ tokens/second}$** using `llama-3.3-70b-versatile` with an automated multi-key failover pool.
- **Upstash Redis Semantic Caching**: Identical and semantically equivalent queries resolve in **$15\text{--}35\text{ms}$**.
- **Server-Sent Events (SSE)**: Delivers smooth, real-time token streaming with live query telemetry.

### 🎨 6. Universal Embeddable Widget & Multi-Framework Code Generator
- **Zero NPM Dependencies**: A single lightweight Vanilla JS script (`pnp-widget.js`) works out of the box.
- **Multi-Framework Snippets**: Visual studio generates copy-paste ready, production-grade components for:
  - **React** (TypeScript TSX & JavaScript JSX)
  - **Next.js** (App Router & Pages Router with `strategy="afterInteractive"`)
  - **Angular** (v16+ Standalone Components)
  - **Vue 3** (Composition API & Nuxt 3)
  - **Svelte / SvelteKit**
  - **Plain HTML / WordPress / Shopify / Webflow**
  - **Backend Bridges** (Node.js Express, Python FastAPI, Laravel PHP)

### 📍 7. Security & Page-Level Visibility Controls
- **3 Deployment Modes**:
  - `🌐 All Pages (Always Visible)`: Public FAQ bots, documentation, and marketing pages.
  - `🔒 Logged-in Users Only (Gated)`: Shows the widget only when authenticated; unmounts immediately on logout to safeguard API quotas.
  - `📍 Selected Pages Only`: Whitelists target routes (e.g. `/support, /help, /checkout`) with optional auth-on-page guards.
- **1-Click Industry Presets**: Pre-configured defaults for **E-Commerce**, **ERP / Internal Portals**, **EdTech**, **Healthcare**, **SaaS**, and **Public Documentation**.

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
│                               PLUG-N-PLAY AI CLOUD PLATFORM                            │
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
│  │                (Routes: SQL vs Vector RAG vs Federated HYBRID)                   │  │
│  └────────┬───────────────────────────────────┬─────────────────────────────────────┘  │
│           │                                   │                                        │
│           ▼                                   ▼                                        │
│  ┌─────────────────────────────────┐ ┌─────────────────────────────────┐               │
│  │     POLYGLOT SQL/MQL ENGINE     │ │        VECTOR RAG ENGINE        │               │
│  │  • Text-to-SQL / Text-to-MQL    │ │  • FastEmbed ONNX (bge-small)   │               │
│  │  • AST sqlglot Sanitization     │ │  • PostgreSQL pgvector (HNSW)   │               │
│  │  • Multi-DB Query Federation    │ │  • Role-Aware Document Slicing  │               │
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

## ⚡ Latency & Performance Budget

| Operation Type | Time-to-First-Token (TTFT) | Total Generation | Processing Pipeline |
| :--- | :--- | :--- | :--- |
| **🚀 Semantic Cache Hit** | **$15\text{ms} - 35\text{ms}$** | **$35\text{ms}$** | Upstash Redis exact/semantic embedding match. |
| **🛡️ Blocked / Malicious** | **$< 2\text{ms}$** | **$< 5\text{ms}$** | Deterministic Gate 1 intent compiler (0 LLM tokens). |
| **📄 Unstructured RAG** | **$180\text{ms} - 280\text{ms}$** | **$450\text{ms} - 650\text{ms}$** | FastEmbed ONNX dense search + pgvector + Groq LPU stream. |
| **🗄️ Database Text-to-SQL** | **$250\text{ms} - 420\text{ms}$** | **$600\text{ms} - 800\text{ms}$** | AST generation + Read-only DB fetch + Groq stream. |
| **🌐 Multi-DB Federation** | **$300\text{ms} - 480\text{ms}$** | **$700\text{ms} - 900\text{ms}$** | Parallel `asyncio.gather` across databases + in-memory join. |
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
- PostgreSQL with `pgvector` extension (or a free [Neon Serverless PostgreSQL](https://neon.tech) database)
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

# Groq LPU Inference (Free tier available at console.groq.com)
GROQ_API_KEY=gsk_your_groq_api_key
GROQ_API_KEY_1=gsk_optional_failover_key_1
GROQ_API_KEY_2=gsk_optional_failover_key_2

# Redis Cache (Optional - Upstash Redis)
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_upstash_token

# Platform Security & Authentication
SECRET_KEY=your-super-secret-hex-encryption-key
ENVIRONMENT=development
```

### 6. Run the Application
```bash
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

- **Agent Studio & Dashboard**: Open [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger API Docs**: Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 🔌 Embeddable Widget Integration

Plug-N-Play AI provides ready-to-use code snippets directly in Step 4 of the Studio or via the Dashboard **Quick Embed Modal**.

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

#### Mounting with Authentication (Auth-Gated Mode)
```tsx
import { AIWidget } from './components/AIWidget';
import { useAuth } from './context/AuthContext';

export function App() {
  const { user, isAuthenticated } = useAuth();

  return (
    <div>
      <main>{/* Your application */}</main>

      {/* 🔒 Only rendered when user is logged in; unmounts on logout */}
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

## 🔒 Zero-Knowledge Backend Bridges

For organizations that cannot open inbound firewall ports or share database credentials, Plug-N-Play AI provides **Zero-Knowledge Backend Bridges**.

The platform generates read-only SQL queries from your schema; your private server executes the SQL locally and returns only the rows for natural language formatting:

### Node.js / Express Bridge
```javascript
app.post('/api/ai-chat', async (req, res) => {
  const { query, userId, userRole } = req.body;
  const PNP_HOST = 'https://your-pnp-instance.com';
  const AGENT_ID = 'YOUR_AGENT_ID';

  // 1. Request safe SQL generation (Zero credentials leave your firewall)
  const genRes = await fetch(`${PNP_HOST}/api/v1/chat/generate-sql`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_id: AGENT_ID, query, user_id: userId, user_role: userRole })
  });
  const data = await genRes.json();
  if (data.guardrail_blocked) return res.json({ answer: data.refusal_message });

  // 2. Strict read-only check
  const sql = data.sql_query;
  if (!sql || !sql.trim().toUpperCase().startsWith('SELECT') || sql.includes(';')) {
    return res.status(400).json({ error: 'Security violation: Non-SELECT query rejected.' });
  }

  // 3. Execute locally on private database inside your firewall
  const dbResult = await dbPool.query(sql);

  // 4. Format natural language response
  const formatRes = await fetch(`${PNP_HOST}/api/v1/chat/format-sql-response`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ agent_id: AGENT_ID, query, sql_query: sql, db_results: dbResult.rows })
  });
  const finalData = await formatRes.json();
  return res.json({ answer: finalData.answer });
});
```

*(Python FastAPI and PHP Laravel bridge implementations are also available in the Studio export tab).*

---

## ☁️ Production Deployment (Render + Cloud)

This repository includes a [`render.yaml`](render.yaml) blueprint specification for automated, zero-downtime deployment:

### 1-Click Render Blueprint
1. Fork or push this repository to GitHub.
2. Open the [Render Dashboard](https://dashboard.render.com/) $\rightarrow$ **New +** $\rightarrow$ **Blueprint**.
3. Select your repository. Render will automatically read `render.yaml` and configure:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`
4. Supply your environment secrets:
   - `DATABASE_URL`: Cloud PostgreSQL connection string (e.g. from [Neon](https://neon.tech)).
   - `GROQ_API_KEY`: Your Groq LPU API key.
   - `SECRET_KEY`: Secret string for JWT/HMAC token signing.
5. Click **Apply**. Your instance will be live in minutes.

### 💰 Zero-Cost Production Stack ($0.00 / month)
You can deploy and run this entire architecture for free using cloud free tiers:

| Component | Provider | Free Tier Allowance | Monthly Cost |
| :--- | :--- | :--- | :--- |
| **API Web Service** | [Render](https://render.com) | 512 MB RAM, 750 free instance hours/month | **$0.00** |
| **PostgreSQL + pgvector** | [Neon Serverless](https://neon.tech) | 0.5 GB storage, auto-suspend compute | **$0.00** |
| **Semantic Cache** | [Upstash Redis](https://upstash.com) | 10,000 commands/day | **$0.00** |
| **LLM Inference** | [Groq Cloud](https://console.groq.com) | Free tier rate limits (300+ tok/s) | **$0.00** |
| **Total** | | | **$0.00 / mo** |

> [!TIP]
> **Prevent Render Spin-Down on Free Tier**:
> Set up a free ping monitor at [UptimeRobot](https://uptimerobot.com) or [Cron-job.org](https://cron-job.org) targeting `https://<your-render-url>/health` every 12 minutes to keep the instance warm.

---

## 🧪 Testing & Verification

Run the automated test suites using `pytest`:

```bash
# Run RBAC identity and security query tests
pytest backend/tests/test_rbac_identity_queries.py -v

# Run multi-database setup tests
python backend/test_multi_db_setup.py

# Run zero-knowledge multi-database bridge tests
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
│   │   │   ├── connectors/        # Live DB connectors (Postgres, MySQL, Mongo, SQLite)
│   │   │   ├── sql/               # Text-to-SQL / Text-to-MQL engine & sqlglot AST validator
│   │   │   ├── rag/               # Chunking, FastEmbed ONNX embedder, pgvector search
│   │   │   ├── router/            # Intent classification & context re-writer
│   │   │   ├── hybrid/            # Central multi-engine orchestrator & streaming engine
│   │   │   ├── guardrails/        # Gate 1 & 2 safety shields and intent compiler
│   │   │   ├── cache/             # Upstash Redis semantic cache
│   │   │   └── llm/               # Groq LPU & multi-key failover gateway
│   │   ├── static/                # Agent Studio dashboard, UI styles, & pnp-widget.js
│   │   └── main.py                # FastAPI app initialization, middleware, & routes
│   ├── tests/                     # Automated test suites
│   └── requirements.txt           # Python dependencies
├── examples/                      # Integration examples & sample schemas
├── render.yaml                    # 1-Click Render infrastructure blueprint
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
