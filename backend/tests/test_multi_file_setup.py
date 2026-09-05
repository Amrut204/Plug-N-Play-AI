import pytest
import uuid
from app.core.database import AsyncSessionLocal, init_db
from app.models.tenants import Tenant
from app.models.agents import Agent
from app.models.rag import RAGSource, RAGChunk
from app.api.v1.quickstart import QuickstartSetupRequest, setup_custom_agent
from sqlalchemy import select


@pytest.mark.asyncio
async def test_setup_custom_agent_with_multiple_documents():
    await init_db()
    
    unique_suffix = uuid.uuid4().hex[:6]
    test_docs = [
        {
            "filename": "leave_policy.pdf",
            "title": "Employee Leave Policy",
            "file_type": "pdf",
            "char_count": 120,
            "content": "Full-time staff members are entitled to 20 business days of paid annual leave per calendar year."
        },
        {
            "filename": "remote_work_agreement.docx",
            "title": "Remote Work Agreement",
            "file_type": "docx",
            "char_count": 140,
            "content": "Remote employees must adhere to standard security protocols including VPN usage and device encryption."
        },
        {
            "filename": "travel_reimbursement.xlsx",
            "title": "Travel Reimbursement Matrix",
            "file_type": "excel",
            "char_count": 110,
            "content": "Domestic travel per diem allowance is capped at $75 per day for meals and incidentals."
        }
    ]

    request_payload = QuickstartSetupRequest(
        project_name=f"Multi-Doc Workspace {unique_suffix}",
        agent_name=f"Policy Assistant {unique_suffix}",
        service_type="rag",
        target_audience="end_user",
        documents=test_docs,
        document_allowed_roles=["employee", "manager"]
    )

    async with AsyncSessionLocal() as session:
        response = await setup_custom_agent(request_payload, session)
        
        assert response["status"] == "success"
        assert response["agent_id"] is not None
        assert response["tenant_id"] is not None
        assert response["chunks_indexed"] >= 3
        assert len(response["test_questions"]) >= 3

        # Verify database entities created
        stmt_sources = select(RAGSource).where(RAGSource.agent_id == response["agent_id"])
        res_sources = await session.execute(stmt_sources)
        sources = res_sources.scalars().all()
        assert len(sources) == 3

        source_names = [s.name for s in sources]
        assert "Employee Leave Policy" in source_names
        assert "Remote Work Agreement" in source_names
        assert "Travel Reimbursement Matrix" in source_names

        # Verify chunks have correct metadata
        stmt_chunks = select(RAGChunk).where(RAGChunk.tenant_id == response["tenant_id"])
        res_chunks = await session.execute(stmt_chunks)
        chunks = res_chunks.scalars().all()
        assert len(chunks) >= 3

        filenames_in_chunks = [c.doc_metadata.get("filename") for c in chunks if c.doc_metadata]
        assert "leave_policy.pdf" in filenames_in_chunks
        assert "remote_work_agreement.docx" in filenames_in_chunks
        assert "travel_reimbursement.xlsx" in filenames_in_chunks
