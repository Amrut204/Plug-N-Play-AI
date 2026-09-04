import pytest
from app.services.rag.chunker import TextChunker
from app.services.rag.embedder import EmbeddingService
from app.services.rag.retriever import RAGRetriever
from app.models.rag import RAGChunk
from app.core.database import AsyncSessionLocal, init_db, Base, engine


@pytest.mark.asyncio
async def test_text_chunking():
    text = (
        "Paragraph 1: College examination attendance requires a minimum of 75%.\n\n"
        "Paragraph 2: Students with less than 65% attendance are detained.\n\n"
        "Paragraph 3: Medical condonations can be granted up to 65%."
    )
    chunks = TextChunker.chunk_text(text, chunk_size=100, chunk_overlap=0)
    assert len(chunks) >= 2


@pytest.mark.asyncio
async def test_embedding_and_retrieval_with_role_permissions():
    await init_db()
    
    async with AsyncSessionLocal() as session:
        import uuid
        from app.models.tenants import Tenant
        tenant_id = f"test-tenant-{uuid.uuid4().hex[:6]}"
        tenant = Tenant(id=tenant_id, name="Test Tenant", slug=f"test-{uuid.uuid4().hex[:6]}")
        session.add(tenant)
        await session.commit()

        source_id = str(uuid.uuid4())
        
        # Doc 1: Public student attendance policy
        content_student = "Students must maintain 75% attendance to sit for end-semester exams."
        vec_student = await EmbeddingService.get_embedding(content_student)
        
        chunk1 = RAGChunk(
            tenant_id=tenant_id,
            rag_source_id=source_id,
            content=content_student,
            doc_metadata={"title": "Exam Attendance", "allowed_roles": ["student", "faculty"]},
            embedding=vec_student
        )
        
        # Doc 2: Faculty confidential payroll policy
        content_faculty = "Faculty members receive annual performance bonuses based on research grants."
        vec_faculty = await EmbeddingService.get_embedding(content_faculty)
        
        chunk2 = RAGChunk(
            tenant_id=tenant_id,
            rag_source_id=source_id,
            content=content_faculty,
            doc_metadata={"title": "Faculty Compensation", "allowed_roles": ["faculty", "admin"]},
            embedding=vec_faculty
        )
        
        session.add_all([chunk1, chunk2])
        await session.commit()
        
        # 1. Student query: Should retrieve attendance chunk and NOT retrieve faculty chunk
        student_results = await RAGRetriever.retrieve_relevant_chunks(
            db=session,
            tenant_id=tenant_id,
            query="What is the exam attendance requirement?",
            user_role="student"
        )
        assert len(student_results) > 0
        assert "75% attendance" in student_results[0]["content"]
        assert not any("Faculty members receive" in r["content"] for r in student_results)
        
        # 2. Faculty query: Should retrieve faculty compensation
        faculty_results = await RAGRetriever.retrieve_relevant_chunks(
            db=session,
            tenant_id=tenant_id,
            query="How are faculty bonuses calculated?",
            user_role="faculty"
        )
        assert len(faculty_results) > 0
        assert "Faculty members receive" in faculty_results[0]["content"]
