import time
import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import httpx

from app.core.database import get_db
from app.core.security import decode_session_token
from app.models.tenants import Tenant
from app.models.agents import Agent
from app.models.chat import ChatSession
from app.models.actions import ActionDefinition, ActionExecutionLog
from app.schemas.actions import (
    ActionCreate,
    ActionResponse,
    ActionExecuteRequest,
    ActionExecuteResponse,
    ActionTestPingRequest,
    BrowserExecutionReportRequest
)
from app.services.actions.dispatcher import ActionDispatcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/actions", tags=["Autonomous Actions & Tools"])


@router.post("/tenant/{tenant_id}/agent/{agent_id}", response_model=ActionResponse, status_code=status.HTTP_201_CREATED)
async def create_action(
    tenant_id: str,
    agent_id: str,
    payload: ActionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Registers a new autonomous Action/Tool for an agent.
    Clients define the API endpoint, parameter requirements, execution mode (server/browser), and role permissions.
    """
    agent = await db.get(Agent, agent_id)
    if not agent or agent.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Agent not found for this tenant.")

    # Convert parameter schemas to serializable list of dicts
    params_data = [p.dict() if hasattr(p, "dict") else dict(p) for p in payload.parameters_schema]

    # Prohibit sensitive banking, payment card, or financial transactions
    clean_name = payload.name.strip().lower().replace(" ", "_")
    check_text = f"{clean_name} {payload.display_name.lower()} {payload.description.lower()}"
    restricted_keywords = [
        "freeze_card", "freeze_debit", "freeze_credit", "transfer_fund", "bank_transfer",
        "wire_transfer", "card_pin", "cvv", "credit_card", "debit_card", "withdraw_cash",
        "lock_card", "payment_card"
    ]
    if any(k in check_text for k in restricted_keywords):
        raise HTTPException(
            status_code=400,
            detail="Autonomous action execution is prohibited for sensitive banking, payment card, or fintech operations. Please use official verified banking portals or live human escalation for financial workflows."
        )

    target_mode = (payload.execution_target or "server").lower()
    if target_mode not in ["server", "browser"]:
        target_mode = "server"

    action = ActionDefinition(
        tenant_id=tenant_id,
        agent_id=agent_id,
        name=clean_name,
        display_name=payload.display_name.strip(),
        description=payload.description.strip(),
        endpoint_url=payload.endpoint_url.strip(),
        http_method=payload.http_method.upper(),
        execution_target=target_mode,
        client_event_name=payload.client_event_name.strip() if payload.client_event_name else None,
        parameters_schema=params_data,
        allowed_roles=payload.allowed_roles,
        requires_user_confirmation=payload.requires_user_confirmation,
        is_active=True
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action


@router.get("/agent/{agent_id}", response_model=List[ActionResponse])
async def list_agent_actions(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Lists all registered actions for an agent.
    """
    stmt = select(ActionDefinition).where(
        ActionDefinition.agent_id == agent_id
    ).order_by(ActionDefinition.created_at.asc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.delete("/{action_id}", status_code=status.HTTP_200_OK)
async def delete_action(
    action_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes an ActionDefinition and associated execution logs.
    """
    action = await db.get(ActionDefinition, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found.")

    await db.delete(action)
    await db.commit()
    return {"status": "success", "message": f"Action '{action.display_name}' deleted successfully."}


@router.post("/execute", response_model=ActionExecuteResponse)
async def execute_action(
    payload: ActionExecuteRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Secure endpoint called by the chat widget when a user confirms an Action Card.
    Validates permissions, cryptographically signs the payload with HMAC-SHA256,
    dispatches to the client's webhook, logs audit telemetry, and synthesizes natural confirmation.
    """
    action = await db.get(ActionDefinition, payload.action_id)
    if not action or not action.is_active:
        raise HTTPException(status_code=404, detail="Action definition not found or is inactive.")

    tenant_id = action.tenant_id
    external_user_id = None
    user_role = "user"
    session_id = payload.session_id

    # Validate authorization token if provided
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        decoded = decode_session_token(token)
        if decoded:
            external_user_id = decoded.get("sub")
            user_role = decoded.get("role", "user")
            tenant_id = decoded.get("tenant_id", tenant_id)

    # Cross-check session if session_id provided
    if session_id:
        chat_session = await db.get(ChatSession, session_id)
        if chat_session:
            if not external_user_id:
                external_user_id = chat_session.external_user_id
            user_role = chat_session.user_role or user_role
            tenant_id = chat_session.tenant_id or tenant_id

    # RBAC Role Verification
    if action.allowed_roles and user_role not in action.allowed_roles and "*" not in action.allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: role '{user_role}' is not authorized to execute '{action.display_name}'."
        )

    # Fetch agent name for tone personalization
    agent = await db.get(Agent, action.agent_id)
    agent_name = agent.name if agent else "Plug-N-Play AI"

    # Defensive check: if action is browser-relay or relative endpoint, server cannot dispatch it directly
    if getattr(action, "execution_target", "server") == "browser" or (action.endpoint_url and action.endpoint_url.startswith("/")):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Action '{action.display_name}' is configured for In-Browser Relay execution ({action.endpoint_url}). "
                "It must be executed directly from the client browser session via window.fetch() rather than cloud webhook dispatch."
            )
        )

    # Dispatch to client endpoint with HMAC signature
    result = await ActionDispatcher.dispatch_action(
        action=action,
        parameters=payload.parameters,
        tenant_id=tenant_id,
        external_user_id=external_user_id,
        session_id=session_id,
        db=db,
        agent_name=agent_name
    )

    return result


@router.post("/report-browser-execution", response_model=ActionExecuteResponse)
async def report_browser_execution(
    payload: BrowserExecutionReportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reports telemetry and outcome of client-side (Browser-Relayed) action executions.
    Records immutable audit log and synthesizes an authoritative BLUF confirmation message.
    """
    action = await db.get(ActionDefinition, payload.action_id)
    if not action:
        raise HTTPException(status_code=404, detail="ActionDefinition not found.")

    agent = await db.get(Agent, action.agent_id)
    agent_name = agent.name if agent else "Plug-N-Play AI"

    is_success = (200 <= payload.response_status < 300)
    raw_response_text = payload.raw_response or (json.dumps(payload.response_data) if payload.response_data else "")

    # Record in audit log
    log_entry = ActionExecutionLog(
        tenant_id=action.tenant_id,
        action_id=action.id,
        session_id=payload.session_id,
        parameters_payload=payload.parameters,
        response_status=payload.response_status,
        response_body=raw_response_text[:3000],
        execution_time_ms=payload.execution_time_ms
    )
    db.add(log_entry)
    await db.commit()

    # Synthesize natural confirmation message
    natural_confirmation = await ActionDispatcher._synthesize_confirmation(
        agent_name=agent_name,
        action=action,
        is_success=is_success,
        response_json=payload.response_data,
        raw_text=raw_response_text,
        parameters=payload.parameters
    )

    return ActionExecuteResponse(
        status="success" if is_success else "failed",
        action_name=action.name,
        display_name=action.display_name,
        response_data=payload.response_data,
        error_message=None if is_success else (raw_response_text or f"HTTP {payload.response_status}"),
        natural_confirmation=natural_confirmation,
        execution_time_ms=payload.execution_time_ms
    )


@router.post("/test-ping")
async def test_action_webhook(payload: ActionTestPingRequest):
    """
    Diagnostic tool for Studio dashboard to test connectivity to client webhook endpoints.
    Sends a test request with mock payload and headers to verify server response.
    """
    start_time = time.perf_counter()
    headers = {
        "Content-Type": "application/json",
        "x-pnp-diagnostic": "true",
        "x-pnp-timestamp": str(int(time.time())),
        "x-pnp-signature": "test_diagnostic_signature_pnp_studio"
    }

    mock_body = payload.mock_payload or {"test": True, "ping": "pong", "source": "Plug-N-Play Studio"}
    body_str = json.dumps(mock_body)
    method = (payload.http_method or "POST").upper()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if method == "PUT":
                res = await client.put(payload.endpoint_url, headers=headers, content=body_str)
            elif method == "PATCH":
                res = await client.patch(payload.endpoint_url, headers=headers, content=body_str)
            else:
                res = await client.post(payload.endpoint_url, headers=headers, content=body_str)

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return {
                "status": "success" if 200 <= res.status_code < 300 else "failed",
                "status_code": res.status_code,
                "latency_ms": latency_ms,
                "response_body": res.text[:1000],
                "endpoint_url": payload.endpoint_url
            }
    except httpx.TimeoutException:
        return {
            "status": "failed",
            "status_code": 504,
            "latency_ms": 10000,
            "response_body": "Endpoint timed out after 10 seconds.",
            "endpoint_url": payload.endpoint_url
        }
    except Exception as exc:
        return {
            "status": "failed",
            "status_code": 500,
            "latency_ms": int((time.perf_counter() - start_time) * 1000),
            "response_body": f"Network connection error: {str(exc)}",
            "endpoint_url": payload.endpoint_url
        }


@router.get("/{action_id}/logs")
async def get_action_logs(
    action_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch recent execution audit logs for an action.
    """
    stmt = select(ActionExecutionLog).where(
        ActionExecutionLog.action_id == action_id
    ).order_by(ActionExecutionLog.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "parameters_payload": l.parameters_payload,
            "response_status": l.response_status,
            "response_body": l.response_body,
            "execution_time_ms": l.execution_time_ms,
            "created_at": l.created_at.isoformat() if l.created_at else None,
            "external_user_id": l.external_user_id
        }
        for l in logs
    ]
