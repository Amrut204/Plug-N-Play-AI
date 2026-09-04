from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.models.rag import RAGSource, RAGChunk
from app.models.agents import Agent
from app.schemas.rag import RAGSourceCreate, RAGSourceResponse, DocumentIngestRequest
from app.core.config import settings
from app.services.rag.chunker import TextChunker
from app.services.rag.embedder import EmbeddingService

router = APIRouter(prefix="/rag", tags=["RAG Knowledge Base"])


@router.post("/sources/{tenant_id}", response_model=RAGSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_rag_source(tenant_id: str, payload: RAGSourceCreate, db: AsyncSession = Depends(get_db)):
    """Create a new RAG knowledge source under an agent."""
    stmt = select(Agent).where(Agent.id == payload.agent_id, Agent.tenant_id == tenant_id)
    result = await db.execute(stmt)
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Agent not found for this tenant.")

    source = RAGSource(
        tenant_id=tenant_id,
        agent_id=payload.agent_id,
        name=payload.name,
        source_type=payload.source_type
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


@router.post("/sources/{source_id}/ingest", status_code=status.HTTP_200_OK)
async def ingest_documents(source_id: str, payload: DocumentIngestRequest, db: AsyncSession = Depends(get_db)):
    """
    Ingests multiple text documents, runs semantic paragraph chunking,
    computes vector embeddings, and stores indexed chunks with role permissions.
    """
    stmt = select(RAGSource).where(RAGSource.id == source_id)
    result = await db.execute(stmt)
    source = result.scalars().first()
    if not source:
        raise HTTPException(status_code=404, detail="RAG Source not found.")

    total_chunks_created = 0

    for doc in payload.documents:
        chunks = TextChunker.chunk_text(
            doc.content, 
            chunk_size=payload.chunk_size, 
            chunk_overlap=payload.chunk_overlap
        )
        if not chunks:
            continue

        # Fast parallel batch vector embeddings
        embeddings = await EmbeddingService.get_embeddings_batch(chunks)

        chunk_meta = {
            "title": doc.title,
            "category": doc.category,
            "allowed_roles": doc.allowed_roles,
            **(doc.metadata or {})
        }
        for chunk_str, embedding_vec in zip(chunks, embeddings):
            rag_chunk = RAGChunk(
                tenant_id=source.tenant_id,
                rag_source_id=source.id,
                content=chunk_str,
                doc_metadata=chunk_meta,
                embedding=embedding_vec
            )
            db.add(rag_chunk)
            total_chunks_created += 1

    await db.commit()
    return {
        "status": "success",
        "documents_processed": len(payload.documents),
        "chunks_indexed": total_chunks_created
    }


from fastapi import UploadFile, File, Form
from typing import Optional, List
from app.services.rag.document_parser import DocumentParser


@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_document_file(
    file: UploadFile = File(...),
    custom_title: Optional[str] = Form(default=None)
):
    """
    Parses an uploaded file (PDF, Excel, CSV, DOCX, TXT, MD), extracts its text,
    and returns the extracted title and content ready for indexing.
    Enforces maximum upload file size guardrail.
    """
    # Guardrail: Check declared file size if provided
    if file.size and file.size > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file exceeds maximum limit of {max_mb}MB."
        )

    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(content_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Uploaded file exceeds maximum limit of {max_mb}MB."
        )

    parsed = DocumentParser.parse_file(file.filename, content_bytes)
    extracted_text = parsed.get("text", "")
    extracted_title = custom_title if (custom_title and custom_title.strip()) else file.filename.rsplit(".", 1)[0].replace("_", " ").title()

    return {
        "filename": file.filename,
        "title": extracted_title,
        "file_type": parsed.get("file_type", "unknown"),
        "content_length": len(extracted_text),
        "content": extracted_text,
        "metadata": parsed,
        "status": "success"
    }


@router.post("/upload-multi", status_code=status.HTTP_200_OK)
async def upload_multiple_files(
    files: List[UploadFile] = File(...)
):
    """
    Parses multiple files in batch (PDF, Excel, CSV, DOCX, TXT), merges their text,
    and returns structured extraction metadata for all files.
    Enforces maximum upload file size guardrail.
    """
    results = []
    combined_texts = []
    total_chars = 0

    for file in files:
        if file.size and file.size > settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{file.filename}' exceeds maximum limit of {max_mb}MB."
            )

        content_bytes = await file.read()
        if not content_bytes:
            continue

        if len(content_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File '{file.filename}' exceeds maximum limit of {max_mb}MB."
            )

        parsed = DocumentParser.parse_file(file.filename, content_bytes)
        results.append(parsed)
        if parsed.get("text"):
            combined_texts.append(f"=== Document: {file.filename} ===\n{parsed['text']}")
            total_chars += len(parsed["text"])

    return {
        "status": "success",
        "file_count": len(results),
        "files": results,
        "total_char_count": total_chars,
        "combined_content": "\n\n".join(combined_texts)
    }

