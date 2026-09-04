from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class RAGSourceCreate(BaseModel):
    agent_id: str
    name: str = Field(...)
    source_type: str = Field(default="file_upload")


class RAGSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    agent_id: str
    name: str
    source_type: str
    created_at: datetime


class DocumentIngestItem(BaseModel):
    title: str
    content: str
    category: Optional[str] = None
    allowed_roles: List[str] = ["student", "faculty", "admin"]
    metadata: Optional[Dict[str, Any]] = None


class DocumentIngestRequest(BaseModel):
    documents: List[DocumentIngestItem]
    chunk_size: int = 500
    chunk_overlap: int = 50


class RAGSearchResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    doc_metadata: Dict[str, Any]
