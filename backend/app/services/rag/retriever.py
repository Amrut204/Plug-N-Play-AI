from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.rag import RAGChunk
from app.services.rag.embedder import EmbeddingService
import logging

logger = logging.getLogger(__name__)


class RAGRetriever:
    """
    Multi-tenant, role-aware RAG vector retriever.
    """

    @classmethod
    async def retrieve_relevant_chunks(
        cls,
        db: AsyncSession,
        tenant_id: str,
        query: str,
        user_role: str = "user",
        top_k: int = 5,
        min_score: float = 0.15
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the top-k most relevant chunks for a user query,
        strictly enforcing tenant boundaries and role-based permissions.
        """
        # 1. Compute query vector
        query_vector = await EmbeddingService.get_embedding(query)

        # 2. Fetch chunks belonging strictly to this tenant
        stmt = select(RAGChunk).where(RAGChunk.tenant_id == tenant_id)
        result = await db.execute(stmt)
        all_chunks = result.scalars().all()

        scored_chunks: List[Dict[str, Any]] = []

        for chunk in all_chunks:
            # 3. Verify Role Permissions
            meta = chunk.doc_metadata or {}
            allowed_roles = meta.get("allowed_roles")
            if allowed_roles and user_role not in allowed_roles and user_role != "admin":
                continue  # Skip chunks this user role is unauthorized to view

            chunk_vec = list(chunk.embedding) if hasattr(chunk.embedding, "__iter__") else chunk.embedding
            if not chunk_vec:
                continue

            similarity = EmbeddingService.cosine_similarity(query_vector, chunk_vec)
            if similarity >= min_score:
                scored_chunks.append({
                    "chunk_id": chunk.id,
                    "source_id": chunk.rag_source_id,
                    "content": chunk.content,
                    "score": round(similarity, 4),
                    "doc_metadata": meta
                })

        # 4. Sort descending by similarity score
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:top_k]
