import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.config import settings

try:
    from pgvector.sqlalchemy import Vector
    _pgvector_supported = True
except ImportError:
    _pgvector_supported = False


def _get_embedding_column():
    """
    Returns Vector(384) when connecting to PostgreSQL with pgvector,
    or JSON array when running on SQLite or under pytest for local test isolation.
    """
    import sys
    if "pytest" in sys.modules or "sqlite" in settings.DATABASE_URL.lower() or not _pgvector_supported:
        return JSON
    return Vector(384)


class RAGSource(Base):
    __tablename__ = "rag_sources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    source_type = Column(String(50), default="file_upload")  # 'file_upload', 'connector_sync', 'api'
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    tenant = relationship("Tenant", back_populates="rag_sources")
    agent = relationship("Agent", back_populates="rag_sources")
    chunks = relationship("RAGChunk", back_populates="source", cascade="all, delete-orphan")


class RAGChunk(Base):
    __tablename__ = "rag_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    rag_source_id = Column(String(36), ForeignKey("rag_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    # Metadata includes allowed_roles (e.g. ["student", "faculty"]), category, document name
    doc_metadata = Column(JSON, default=dict)
    # 384-dimensional FastEmbed vector (native pgvector in Postgres, JSON list in SQLite)
    embedding = Column(_get_embedding_column(), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    source = relationship("RAGSource", back_populates="chunks")
