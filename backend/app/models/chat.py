import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, JSON, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    external_user_id = Column(String(255), nullable=True)  # e.g. "STU_1001"
    user_role = Column(String(50), default="user")          # e.g. "student", "faculty", "admin"
    is_escalated = Column(Boolean, default=False, index=True)
    escalation_reason = Column(Text, nullable=True)
    escalation_contact = Column(String(255), nullable=True)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    agent = relationship("Agent", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    query_logs = relationship("QueryLog", back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system', 'tool'
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, default=dict)
    feedback_rating = Column(Integer, nullable=True)  # +1 (thumbs up), -1 (thumbs down)
    feedback_comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("ChatSession", back_populates="messages")


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    user_query = Column(Text, nullable=False)
    route_chosen = Column(String(50), nullable=False)  # 'SQL', 'RAG', 'HYBRID', 'DIRECT'
    generated_sql = Column(Text, nullable=True)
    sql_execution_ms = Column(Integer, nullable=True)
    rag_retrieval_ms = Column(Integer, nullable=True)
    llm_generation_ms = Column(Integer, nullable=True)
    total_tokens = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="query_logs")
    session = relationship("ChatSession", back_populates="query_logs")
