from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class ActionParameter(BaseModel):
    name: str = Field(..., description="Parameter name, e.g. order_id, reason, appointment_date")
    type: str = Field(default="string", description="Parameter data type: string, number, integer, boolean")
    description: Optional[str] = Field(default="", description="Description of the parameter to help LLM extract accurately")
    required: bool = Field(default=True, description="Whether this parameter is mandatory")
    default: Optional[Any] = Field(default=None, description="Default value if not supplied")


class ActionCreate(BaseModel):
    name: str = Field(..., examples=["cancel_order"], description="Unique machine identifier for tool calling")
    display_name: str = Field(..., examples=["Cancel Order"], description="Human-friendly action name shown on the widget card")
    description: str = Field(..., examples=["Cancels a customer order and initiates payment refund"], description="Detailed purpose for LLM intent routing")
    endpoint_url: str = Field(..., examples=["https://api.store.com/orders/cancel", "/api/orders/cancel"], description="Target webhook/API endpoint (absolute for server, or relative for browser relay)")
    http_method: str = Field(default="POST", examples=["POST"], description="HTTP method: POST, PUT, or PATCH")
    execution_target: str = Field(default="server", examples=["server", "browser"], description="'server' (backend-to-backend HMAC webhook) or 'browser' (in-browser relay with session cookies)")
    client_event_name: Optional[str] = Field(default=None, examples=["pnp:action:execute"], description="Optional CustomEvent name for WebSocket/SPA client apps")
    parameters_schema: List[ActionParameter] = Field(default_factory=list, description="List of expected input parameters")
    allowed_roles: List[str] = Field(default=["user", "student", "admin"], description="Roles authorized to execute this action")
    requires_user_confirmation: bool = Field(default=True, description="Whether to show confirmation card before executing")


class ActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    agent_id: str
    name: str
    display_name: str
    description: str
    endpoint_url: str
    http_method: str
    execution_target: str = "server"
    client_event_name: Optional[str] = None
    parameters_schema: List[Dict[str, Any]]
    allowed_roles: List[str]
    requires_user_confirmation: bool
    is_active: bool
    created_at: datetime


class ActionExecuteRequest(BaseModel):
    action_id: str = Field(..., description="UUID of the ActionDefinition to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Extracted parameters for this action")
    session_id: Optional[str] = Field(default=None, description="Optional chat session ID for audit logging")


class BrowserExecutionReportRequest(BaseModel):
    action_id: str = Field(..., description="UUID of the ActionDefinition executed")
    session_id: Optional[str] = Field(default=None, description="Chat session ID for audit logging")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters executed client-side")
    response_status: int = Field(default=200, description="HTTP status code received by browser (e.g. 200, 400)")
    response_data: Optional[Dict[str, Any]] = Field(default=None, description="Parsed JSON response from client endpoint")
    raw_response: Optional[str] = Field(default=None, description="Raw text response from client endpoint")
    execution_time_ms: int = Field(default=0, description="Client-side execution latency in milliseconds")


class ActionExecuteResponse(BaseModel):
    status: str = Field(..., description="'success' or 'failed'")
    action_name: str
    display_name: str
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    natural_confirmation: str = Field(..., description="Authoritative BLUF natural language explanation of the action outcome")
    execution_time_ms: int = 0


class ActionTestPingRequest(BaseModel):
    endpoint_url: str
    http_method: str = "POST"
    mock_payload: Optional[Dict[str, Any]] = None
