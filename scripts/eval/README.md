# Live Evaluation & Benchmark Scripts

This directory contains standalone integration tests and evaluation suites designed to verify live endpoints and database connections.

## Available Scripts

| Script | Purpose | Target |
|---|---|---|
| `agent_eval.py` | Autonomous red-teaming, RAG grounding & jailbreak defense suite | Deployed / Staging |
| `comprehensive_suite.py` | Full multi-file parsing, self-healing reflection, and agent verification | `localhost:8000` |
| `zero_knowledge_bridge.py` | End-to-end zero-knowledge schema-only Text-to-SQL workflow | `localhost:8000` |
| `zk_multi_db.py` | Multi-database federated DDL parsing and safe query routing | `localhost:8000` |
| `multi_db_setup.py` | Direct verification of federated database setups | `localhost:8000` |
| `streaming_multiagent_e2e.py` | Real-time SSE token streaming and multi-turn message verification | `localhost:8000` |
| `escalation_webhook.py` | Human-in-the-loop and webhook notification verification | `localhost:8000` |

## Running

Ensure your local backend server is running (`uvicorn app.main:app --app-dir backend --port 8000`), then execute:

```bash
python scripts/eval/comprehensive_suite.py
python scripts/eval/zero_knowledge_bridge.py
```
