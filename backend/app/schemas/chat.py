from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class SessionCreateRequest(BaseModel):
    agent_id: str
    external_user_id: str = Field(..., example="STU_1001")
    user_role: str = Field(default="student", example="student")
    metadata: Optional[Dict[str, Any]] = None
    expires_minutes: int = Field(default=15, ge=1, le=1440)


class SessionResponse(BaseModel):
    session_id: str
    session_token: str
    agent_id: str
    external_user_id: str
    user_role: str
    expires_at: datetime


class ChatMessageRequest(BaseModel):
    query: str = Field(..., example="What is my attendance in Mathematics and can I sit for the exam?")
    stream: bool = True


class ChatResponsePayload(BaseModel):
    answer: str
    route_chosen: str  # 'SQL', 'RAG', 'HYBRID', 'DIRECT', 'ACTION_PROPOSAL'
    action_proposal: Optional[Dict[str, Any]] = None
    structured_data: Optional[List[Dict[str, Any]]] = None
    rag_sources: Optional[List[Dict[str, Any]]] = None
    reasoning_summary: Optional[str] = None
    session_id: str
    message_id: Optional[str] = None
    cached: bool = False


class ChatFeedbackRequest(BaseModel):
    message_id: Optional[str] = None
    session_id: Optional[str] = None
    rating: int = Field(..., description="+1 for thumbs up, -1 for thumbs down")
    comment: Optional[str] = None


class ChatFeedbackResponse(BaseModel):
    status: str = "success"
    message: str = "Feedback recorded."
