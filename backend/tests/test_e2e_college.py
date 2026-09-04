import os
import sys
import pytest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, init_db
from app.models.tenants import Tenant, ApiKey
from app.models.agents import Agent
from app.models.connections import Connection, SemanticTable, SemanticColumn
from app.models.rag import RAGSource, RAGChunk
from app.models.chat import ChatSession
from app.services.hybrid.orchestrator import QueryOrchestrator
from app.core.security import create_widget_session_token

# Import College ERP app using importlib to avoid collision with backend.app
import importlib.util
COLLEGE_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "examples", "college-erp"))
college_app_path = os.path.join(COLLEGE_APP_DIR, "app.py")
spec = importlib.util.spec_from_file_location("college_erp_app", college_app_path)
college_erp_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(college_erp_module)

college_app = college_erp_module.app
COLLEGE_SHARED_SECRET = college_erp_module.SHARED_SECRET


@pytest.mark.asyncio
async def test_full_college_erp_lifecycle_e2e(monkeypatch):
    """
    Master end-to-end milestone test:
    Validates Tenant setup, Connector schema sync, RAG ingestion,
    and executes SQL, RAG, and Hybrid queries.
    """
    await init_db()
    
    # Intercept outbound connector HTTP calls to testserver and route directly to college_app via ASGITransport
    transport = httpx.ASGITransport(app=college_app)
    real_async_client = httpx.AsyncClient

    def mock_client_factory(*args, **kwargs):
        # Route testserver calls to college_app while allowing external LLM API calls (e.g. Groq) to pass through
        mounts = dict(kwargs.get("mounts") or {})
        mounts["http://testserver"] = transport
        mounts["https://testserver"] = transport
        kwargs["mounts"] = mounts
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", mock_client_factory)

    async with AsyncSessionLocal() as session:
        # 1. Create Tenant (unique slug for repeatable tests)
        import uuid
        test_slug = f"apex-institute-{uuid.uuid4().hex[:6]}"
        tenant = Tenant(name="Apex Institute of Technology", slug=test_slug)
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        # 2. Create AI Agent
        agent = Agent(
            tenant_id=tenant.id,
            name="Apex Student AI Advisor",
            system_prompt="You are the official academic assistant for Apex Institute."
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)

        # 3. Register College ERP Connection
        connection = Connection(
            tenant_id=tenant.id,
            name="Apex College ERP Production Gateway",
            connection_type="connector_http",
            endpoint_url="http://testserver/api/v1/connector",
            auth_secret_hash=COLLEGE_SHARED_SECRET
        )
        session.add(connection)
        await session.commit()
        await session.refresh(connection)

        # 4. Synchronize Schema from College ERP Connector
        from app.api.v1.connections import sync_schema_from_connector
        sync_result = await sync_schema_from_connector(connection.id, session)
        assert sync_result["status"] == "success"
        assert set(sync_result["synced_tables"]) == {"students", "attendance", "marks", "fees"}

        # Verify semantic columns & row identity binding stored
        stmt = select(SemanticTable).where(SemanticTable.connection_id == connection.id)
        res = await session.execute(stmt)
        tables = res.scalars().all()
        assert len(tables) == 4

        # 5. Ingest College Policy Documents into RAG Engine
        rag_source = RAGSource(
            tenant_id=tenant.id,
            agent_id=agent.id,
            name="College Academic & Examination Rules"
        )
        session.add(rag_source)
        await session.commit()
        await session.refresh(rag_source)

        policies_dir = os.path.join(COLLEGE_APP_DIR, "policies")
        from app.api.v1.rag import ingest_documents
        from app.schemas.rag import DocumentIngestRequest, DocumentIngestItem

        doc_items = []
        for filename in os.listdir(policies_dir):
            if filename.endswith(".md"):
                file_path = os.path.join(policies_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                doc_items.append(DocumentIngestItem(
                    title=filename.replace(".md", "").replace("_", " ").title(),
                    content=content,
                    category="Policy",
                    allowed_roles=["student", "faculty", "admin"]
                ))

        ingest_req = DocumentIngestRequest(documents=doc_items, chunk_size=400, chunk_overlap=50)
        ingest_res = await ingest_documents(rag_source.id, ingest_req, session)
        assert ingest_res["status"] == "success"
        assert ingest_res["chunks_indexed"] > 0

        # 6. Initialize Student Session (Alex Johnson - STU_1001)
        student_session = ChatSession(
            tenant_id=tenant.id,
            agent_id=agent.id,
            external_user_id="STU_1001",
            user_role="student"
        )
        session.add(student_session)
        await session.commit()
        await session.refresh(student_session)

        # 7. Milestone Query 1: Pure SQL Query
        sql_query = "What is my attendance percentage in Database Systems?"
        res_sql = await QueryOrchestrator.process_query(session, student_session, sql_query)
        assert res_sql["route_chosen"] == "SQL"
        assert res_sql["structured_data"] is not None
        attendance_records = res_sql["structured_data"]
        assert any(
            r.get("attendance_percentage") == 71.1 or r.get("subject") == "Database Systems"
            for r in attendance_records
        )

        # 8. Milestone Query 2: Pure RAG Query
        rag_query = "What is the institutional policy regarding examination attendance?"
        res_rag = await QueryOrchestrator.process_query(session, student_session, rag_query)
        assert res_rag["route_chosen"] == "RAG"
        assert res_rag["rag_sources"] is not None
        assert len(res_rag["rag_sources"]) > 0
        assert any("75%" in c["content"] for c in res_rag["rag_sources"])

        # 9. Milestone Query 3: HYBRID Query (SQL + RAG Reasoning)
        hybrid_query = "Can I sit for the exam considering my current attendance in Database Systems?"
        res_hybrid = await QueryOrchestrator.process_query(session, student_session, hybrid_query)
        assert res_hybrid["route_chosen"] == "HYBRID"
        assert res_hybrid["structured_data"] is not None
        assert res_hybrid["rag_sources"] is not None
        assert "71%" in res_hybrid["answer"] or "72%" in res_hybrid["answer"] or "75%" in res_hybrid["answer"]
        print("\n--- HYBRID REASONING RESPONSE ---")
        print(res_hybrid["answer"])
        print("---------------------------------")
