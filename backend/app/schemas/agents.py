from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class AgentCreate(BaseModel):
    name: str = Field(...)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_provider: str = Field(default="openai")
    model_name: str = Field(default="gpt-4o-mini")
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    guardrail_config: Optional[str] = None
    allowed_domains: Optional[str] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    guardrail_config: Optional[str] = None
    allowed_domains: Optional[str] = None
    is_active: Optional[bool] = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: str
    description: Optional[str]
    system_prompt: Optional[str]
    model_provider: str
    model_name: str
    temperature: float
    guardrail_config: Optional[str] = None
    allowed_domains: Optional[str] = None
    is_active: bool
    created_at: datetime
