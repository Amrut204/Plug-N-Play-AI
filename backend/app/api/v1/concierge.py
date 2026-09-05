import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_session_token
from app.models.tenants import Tenant
from app.models.agents import Agent
from app.models.connections import Connection
from app.models.rag import RAGSource
from app.services.concierge.concierge_service import PlatformConciergeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/concierge", tags=["Platform Concierge & Guide"])


class ConciergeChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question about the platform or their workspace")
    stream: bool = Field(default=True, description="Enable Server-Sent Events (SSE) streaming")
    history: Optional[List[Dict[str, str]]] = Field(default=None, description="Optional previous chat history")


class ConciergeChatResponse(BaseModel):
    answer: str
    route_chosen: str = "PLATFORM_GUIDE"
    is_authenticated: bool
    workspace_name: Optional[str] = None


async def resolve_user_context(
    authorization: Optional[str],
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Extract verified tenant context from JWT Bearer token.
    Guarantees strict tenant isolation by only looking up the authenticated user's workspace.
    Queries live telemetry: configured agents, connected databases, and RAG sources.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return {"is_authenticated": False}

    token = authorization[7:].strip()
    if not token:
        return {"is_authenticated": False}

    decoded = decode_session_token(token)
    if not decoded:
        return {"is_authenticated": False}

    tenant_id = decoded.get("tenant_id") or decoded.get("sub")
    if not tenant_id:
        return {"is_authenticated": False}

    try:
        stmt = select(Tenant).where(Tenant.id == str(tenant_id))
        res = await db.execute(stmt)
        tenant = res.scalars().first()

        if tenant:
            # Query workspace live telemetry & resources
            agents = []
            connections = []
            rag_count = 0
            try:
                stmt_agents = select(Agent).where(Agent.tenant_id == tenant.id)
                res_agents = await db.execute(stmt_agents)
                agents = res_agents.scalars().all()

                stmt_conn = select(Connection).where(Connection.tenant_id == tenant.id)
                res_conn = await db.execute(stmt_conn)
                connections = res_conn.scalars().all()

                stmt_rag = select(RAGSource).where(RAGSource.tenant_id == tenant.id)
                res_rag = await db.execute(stmt_rag)
                rag_count = len(res_rag.scalars().all())
            except Exception as res_err:
                logger.warning(f"[Concierge] Error querying workspace resources: {res_err}")

            return {
                "is_authenticated": True,
                "tenant_id": tenant.id,
                "workspace_name": tenant.name,
                "full_name": tenant.full_name or tenant.name,
                "email": tenant.email,
                "tier": tenant.subscription_tier or "free",
                "agent_count": len(agents),
                "agents": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "description": a.description or "",
                        "model": a.model_name or "gpt-4o-mini",
                        "is_active": a.is_active
                    }
                    for a in agents
                ],
                "connection_count": len(connections),
                "connections": [
                    {
                        "name": c.name,
                        "type": c.connection_type
                    }
                    for c in connections
                ],
                "document_count": rag_count
            }
    except Exception as e:
        logger.warning(f"[Concierge] Error resolving tenant context: {e}")

    # Fallback to token payload claims if DB row lookup is non-standard
    if decoded.get("email"):
        return {
            "is_authenticated": True,
            "tenant_id": str(tenant_id),
            "workspace_name": decoded.get("slug") or "Your Workspace",
            "full_name": decoded.get("email"),
            "email": decoded.get("email"),
            "tier": "active"
        }

    return {"is_authenticated": False}


@router.post("/chat")
async def concierge_chat(
    payload: ConciergeChatRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Direct technical concierge chat endpoint for the Plug-N-Play AI website.
    Grounded exclusively on the platform knowledge guide with verified tenant isolation.
    Contains zero database query execution capabilities.
    """
    user_context = await resolve_user_context(authorization, db)

    if payload.stream:
        async def event_generator():
            # Initial meta event
            meta_payload = {
                "event": "meta",
                "route": "PLATFORM_GUIDE",
                "is_authenticated": user_context.get("is_authenticated", False),
                "workspace_name": user_context.get("workspace_name")
            }
            yield f"data: {json.dumps(meta_payload)}\n\n"

            # Stream tokens
            try:
                async for token in PlatformConciergeService.stream_ask(
                    user_query=payload.query,
                    user_context=user_context,
                    history=payload.history
                ):
                    chunk_payload = {
                        "event": "token",
                        "token": token
                    }
                    yield f"data: {json.dumps(chunk_payload)}\n\n"
            except Exception as e:
                logger.error(f"[Concierge] Stream error: {e}")
                err_payload = {
                    "event": "token",
                    "token": f"\n\n*Service notification: Response encountered an issue ({str(e)}). Please retry.*"
                }
                yield f"data: {json.dumps(err_payload)}\n\n"

            # Done event
            yield f"data: {json.dumps({'event': 'done'})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    # Non-streaming fallback
    try:
        answer = await PlatformConciergeService.ask(
            user_query=payload.query,
            user_context=user_context,
            history=payload.history
        )
    except Exception as e:
        logger.error(f"[Concierge] Non-streaming error: {e}")
        answer = PlatformConciergeService.generate_grounded_fallback(payload.query, user_context)

    return ConciergeChatResponse(
        answer=answer,
        route_chosen="PLATFORM_GUIDE",
        is_authenticated=user_context.get("is_authenticated", False),
        workspace_name=user_context.get("workspace_name")
    )
