from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class TenantCreate(BaseModel):
    name: str = Field(...)
    slug: str = Field(...)


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    is_active: bool
    created_at: datetime


class ApiKeyCreate(BaseModel):
    name: str = Field(...)
    role: str = Field(default="connector")


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    role: str
    api_key: Optional[str] = None
    created_at: datetime
