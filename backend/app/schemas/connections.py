from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class SemanticColumnCreate(BaseModel):
    column_name: str
    data_type: str
    business_meaning: str
    allowed_operations: List[str] = ["SELECT", "WHERE", "JOIN"]
    is_sensitive: bool = False
    row_identity_binding: Optional[str] = None  # e.g. "auth_user_id"


class SemanticColumnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    column_name: str
    data_type: str
    business_meaning: str
    allowed_operations: List[str]
    is_sensitive: bool
    row_identity_binding: Optional[str]


class SemanticTableCreate(BaseModel):
    table_name: str
    business_name: Optional[str] = None
    description: Optional[str] = None
    is_queryable: bool = True
    allowed_roles: List[str] = ["admin", "user", "student", "faculty"]
    columns: List[SemanticColumnCreate] = []


class SemanticTableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    table_name: str
    business_name: Optional[str]
    description: Optional[str]
    is_queryable: bool
    allowed_roles: List[str]
    columns: List[SemanticColumnResponse] = []


class ConnectionCreate(BaseModel):
    name: str = Field(...)
    connection_type: str = Field(default="connector_http")
    endpoint_url: str = Field(...)
    shared_secret: str = Field(...)


class ConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    name: str
    connection_type: str
    endpoint_url: Optional[str]
    is_active: bool
    created_at: datetime
    tables: List[SemanticTableResponse] = []
