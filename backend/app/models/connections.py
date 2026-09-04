import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class Connection(Base):
    __tablename__ = "connections"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    connection_type = Column(String(50), default="connector_http")  # 'connector_http', 'direct_postgres_readonly'
    endpoint_url = Column(String(500), nullable=True)               # e.g. http://client-app:5000/api/v1/connector
    auth_secret_hash = Column(String(255), nullable=True)           # HMAC secret
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    tenant = relationship("Tenant", back_populates="connections")
    tables = relationship("SemanticTable", back_populates="connection", cascade="all, delete-orphan")


class SemanticTable(Base):
    __tablename__ = "semantic_tables"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    connection_id = Column(String(36), ForeignKey("connections.id", ondelete="CASCADE"), nullable=False, index=True)
    table_name = Column(String(255), nullable=False)
    business_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_queryable = Column(Boolean, default=True)
    allowed_roles = Column(JSON, default=lambda: ["admin", "user", "student", "faculty"])

    # Relationships
    connection = relationship("Connection", back_populates="tables")
    columns = relationship("SemanticColumn", back_populates="table", cascade="all, delete-orphan")


class SemanticColumn(Base):
    __tablename__ = "semantic_columns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    table_id = Column(String(36), ForeignKey("semantic_tables.id", ondelete="CASCADE"), nullable=False, index=True)
    column_name = Column(String(255), nullable=False)
    data_type = Column(String(50), nullable=False)
    business_meaning = Column(Text, nullable=False)
    allowed_operations = Column(JSON, default=lambda: ["SELECT", "WHERE", "JOIN"])
    is_sensitive = Column(Boolean, default=False)
    row_identity_binding = Column(String(100), nullable=True)  # e.g. "auth_user_id" -> maps to student_id or user_id

    # Relationships
    table = relationship("SemanticTable", back_populates="columns")
