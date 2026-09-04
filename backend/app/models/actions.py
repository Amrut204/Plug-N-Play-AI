import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Integer, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class ActionDefinition(Base):
    __tablename__ = "action_definitions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)                  # e.g. "cancel_order", "submit_medical_appeal"
    display_name = Column(String(255), nullable=False)          # e.g. "Cancel Order"
    description = Column(Text, nullable=False)                  # Plain English description for LLM tool selection
    
    endpoint_url = Column(String(500), nullable=False)          # Target client webhook URL or relative endpoint
    http_method = Column(String(10), default="POST")            # POST / PUT / PATCH
    execution_target = Column(String(50), default="server")     # "server" (backend HMAC webhook) or "browser" (in-browser relay)
    client_event_name = Column(String(100), nullable=True)      # Optional CustomEvent name for WebSocket/SPA apps
    
    # JSON schema defining required fields (name, type, description, required, default)
    parameters_schema = Column(JSON, nullable=False, default=list)
    
    allowed_roles = Column(JSON, default=lambda: ["user", "student", "admin"])
    requires_user_confirmation = Column(Boolean, default=True)  # True = shows interactive card in widget
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    tenant = relationship("Tenant")
    agent = relationship("Agent")
    execution_logs = relationship("ActionExecutionLog", back_populates="action", cascade="all, delete-orphan")


class ActionExecutionLog(Base):
    __tablename__ = "action_execution_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    action_id = Column(String(36), ForeignKey("action_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    external_user_id = Column(String(255), nullable=True)
    
    parameters_payload = Column(JSON, nullable=False, default=dict)
    response_status = Column(Integer, nullable=True)            # HTTP status from client endpoint (e.g. 200, 400, 500)
    response_body = Column(Text, nullable=True)                 # Raw response string/JSON
    execution_time_ms = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    action = relationship("ActionDefinition", back_populates="execution_logs")
    session = relationship("ChatSession")
