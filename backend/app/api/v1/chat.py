import json
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Any
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import create_widget_session_token, decode_session_token
from app.models.agents import Agent
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import SessionCreateRequest, SessionResponse, ChatMessageRequest, ChatResponsePayload
from app.services.hybrid.orchestrator import QueryOrchestrator
from app.services.cache.redis_cache import RedisService

router = APIRouter(prefix="/chat", tags=["Widget Chat & Sessions"])


@router.post("/sessions/create", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(payload: SessionCreateRequest, db: AsyncSession = Depends(get_db)):
    """
    Called by Client Backend to initialize a secure short-lived AI session for a logged-in user.
    Returns a signed JWT session token for the embeddable widget.
    """
    stmt = select(Agent).where(Agent.id == payload.agent_id)
    result = await db.execute(stmt)
    agent = result.scalars().first()
    if not agent:
        # Fall back to first active agent for zero-friction demo and testing
        stmt_fb = select(Agent).where(Agent.is_active == True)
        res_fb = await db.execute(stmt_fb)
        agent = res_fb.scalars().first()

    if not agent:
        raise HTTPException(status_code=404, detail="No active Agent configured.")

    session = ChatSession(
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        external_user_id=payload.external_user_id,
        user_role=payload.user_role
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    token = create_widget_session_token(
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        external_user_id=payload.external_user_id,
        user_role=payload.user_role,
        metadata=payload.metadata,
        expires_minutes=payload.expires_minutes
    )

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=payload.expires_minutes)

    return SessionResponse(
        session_id=session.id,
        session_token=token,
        agent_id=agent.id,
        external_user_id=payload.external_user_id,
        user_role=payload.user_role,
        expires_at=expires_at
    )


@router.post("/message", response_model=ChatResponsePayload)
async def send_chat_message(
    payload: ChatMessageRequest,
    authorization: Optional[str] = Header(None),
    session_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a chat message query against the Plug-N-Play AI Data Layer.
    Requires a valid short-lived session token in the Authorization header or an explicit session_id.
    """
    session = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        decoded = decode_session_token(token)
        if not decoded:
            raise HTTPException(status_code=401, detail="Invalid or expired session token.")
        
        # Look up or create session for token
        sub = decoded.get("sub")
        role = decoded.get("role", "user")
        tenant_id = decoded.get("tenant_id")
        agent_id = decoded.get("agent_id")

        if session_id:
            stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.tenant_id == tenant_id)
            res = await db.execute(stmt)
            session = res.scalars().first()

        if not session:
            session = ChatSession(
                tenant_id=tenant_id,
                agent_id=agent_id,
                external_user_id=sub,
                user_role=role
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
    elif session_id:
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        res = await db.execute(stmt)
        session = res.scalars().first()

    if not session:
        raise HTTPException(status_code=401, detail="Missing or invalid session credentials.")

    # Distributed Rate Limiting via Redis
    rate_key = f"{session.tenant_id}:{session.external_user_id or session.id}"
    allowed, current_count, retry_after = await RedisService.check_rate_limit(rate_key, limit=60, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum 60 requests per minute. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )

    # Save user message
    user_msg = ChatMessage(session_id=session.id, role="user", content=payload.query)
    db.add(user_msg)
    await db.commit()

    # Process through Query Orchestrator
    result = await QueryOrchestrator.process_query(db, session, payload.query)

    # Save assistant message
    asst_msg = ChatMessage(
        session_id=session.id, 
        role="assistant", 
        content=result["answer"],
        metadata_json={
            "route_chosen": result["route_chosen"],
            "generated_sql": result["generated_sql"]
        }
    )
    db.add(asst_msg)
    await db.commit()
    await db.refresh(asst_msg)

    return ChatResponsePayload(
        answer=result["answer"],
        route_chosen=result["route_chosen"],
        action_proposal=result.get("action_proposal"),
        structured_data=result["structured_data"],
        rag_sources=result["rag_sources"],
        reasoning_summary=f"Processed via {result['route_chosen']} engine",
        session_id=session.id,
        message_id=asst_msg.id,
        cached=result.get("cached", False)
    )


@router.post("/stream")
async def stream_chat_post(
    payload: ChatMessageRequest,
    authorization: Optional[str] = Header(None),
    session_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    POST Server-Sent Events (SSE) streaming endpoint.
    Streams structured events (meta, token, done) for real-time typewriter fluid UI.
    """
    session = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        decoded = decode_session_token(token)
        if not decoded:
            raise HTTPException(status_code=401, detail="Invalid or expired session token.")

        sub = decoded.get("sub")
        role = decoded.get("role", "user")
        tenant_id = decoded.get("tenant_id")
        agent_id = decoded.get("agent_id")

        if session_id:
            stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.tenant_id == tenant_id)
            res = await db.execute(stmt)
            session = res.scalars().first()

        if not session:
            session = ChatSession(
                tenant_id=tenant_id,
                agent_id=agent_id,
                external_user_id=sub,
                user_role=role
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
    elif session_id:
        stmt = select(ChatSession).where(ChatSession.id == session_id)
        res = await db.execute(stmt)
        session = res.scalars().first()

    if not session:
        raise HTTPException(status_code=401, detail="Missing or invalid session credentials.")

    # Save user message
    user_msg = ChatMessage(session_id=session.id, role="user", content=payload.query)
    db.add(user_msg)
    await db.commit()

    return StreamingResponse(
        QueryOrchestrator.stream_query(db, session, payload.query),
        media_type="text/event-stream"
    )


@router.get("/stream")
async def stream_chat_get(
    query: str = Query(...),
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    GET Server-Sent Events (SSE) streaming endpoint for browser EventSource.
    """
    decoded = decode_session_token(token)
    if not decoded:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")

    session = ChatSession(
        tenant_id=decoded["tenant_id"],
        agent_id=decoded["agent_id"],
        external_user_id=decoded.get("sub"),
        user_role=decoded.get("role", "user")
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Save user message
    user_msg = ChatMessage(session_id=session.id, role="user", content=query)
    db.add(user_msg)
    await db.commit()

    return StreamingResponse(
        QueryOrchestrator.stream_query(db, session, query),
        media_type="text/event-stream"
    )


@router.post("/feedback")
async def record_message_feedback(
    payload: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Record user thumbs up (+1) or thumbs down (-1) feedback on an assistant message.
    """
    msg_id = payload.get("message_id")
    session_id = payload.get("session_id")
    rating = int(payload.get("rating", 1))
    comment = payload.get("comment")

    if msg_id:
        stmt = select(ChatMessage).where(ChatMessage.id == msg_id)
        res = await db.execute(stmt)
        msg = res.scalars().first()
        if msg:
            msg.feedback_rating = rating
            if comment:
                msg.feedback_comment = comment
            await db.commit()
            return {"status": "success", "message": "Feedback recorded."}

    # Fallback to last assistant message in session
    if session_id:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id, ChatMessage.role == "assistant")
            .order_by(ChatMessage.created_at.desc())
        )
        res = await db.execute(stmt)
        msg = res.scalars().first()
        if msg:
            msg.feedback_rating = rating
            if comment:
                msg.feedback_comment = comment
            await db.commit()
            return {"status": "success", "message": "Feedback recorded for last message."}

    return {"status": "recorded", "message": "Feedback noted."}



from pydantic import BaseModel
from app.models.connections import Connection, SemanticTable, SemanticColumn
from app.services.sql.generator import TextToSQLEngine
from app.services.guardrails.compiler import AIGuardrailCompiler
from app.services.llm.gateway import LLMGateway
from sqlalchemy.orm import selectinload


class GenerateSQLRequest(BaseModel):
    agent_id: str
    query: str
    user_id: Optional[str] = None
    user_role: Optional[str] = "user"
    dialect: Optional[str] = "postgres"


class FormatSQLResponseRequest(BaseModel):
    agent_id: str
    query: str
    sql_query: str
    db_results: Any
    user_role: Optional[str] = "user"


@router.post("/generate-sql", status_code=status.HTTP_200_OK)
async def generate_sql_for_client_bridge(payload: GenerateSQLRequest, db: AsyncSession = Depends(get_db)):
    """
    Zero-Knowledge DB Bridge: Generates a safe, AST-validated SQL query
    from the client's registered schema for their backend server to execute locally.
    No database credentials or host URLs are needed.
    """
    stmt = select(Agent).where(Agent.id == payload.agent_id)
    res = await db.execute(stmt)
    agent = res.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")

    # 1. Gate 1 Guardrail Check
    guardrail_config = json.loads(agent.guardrail_config) if agent.guardrail_config else {}
    banned_intents = guardrail_config.get("banned_intents", [])
    restricted_columns = set(guardrail_config.get("restricted_columns", []))

    for intent in banned_intents:
        if intent.replace("_", " ") in payload.query.lower():
            return {
                "status": "blocked",
                "guardrail_blocked": True,
                "refusal_message": guardrail_config.get("refusal_message", "Request blocked by enterprise security guardrails."),
                "sql_query": None
            }

    # 2. Fetch Semantic Tables
    c_stmt = (
        select(Connection)
        .where(Connection.tenant_id == agent.tenant_id, Connection.is_active == True)
        .options(selectinload(Connection.tables).selectinload(SemanticTable.columns))
    )
    c_res = await db.execute(c_stmt)
    conn = c_res.scalars().first()
    if not conn or not conn.tables:
        raise HTTPException(status_code=400, detail="No database schema registered for this agent.")

    allowed_tables = {t.table_name for t in conn.tables}
    allowed_columns = {t.table_name: {c.column_name for c in t.columns} for t in conn.tables}

    schema_context = TextToSQLEngine.build_schema_context(
        tables=conn.tables,
        user_role=payload.user_role or "user",
        user_query=payload.query,
        restricted_columns=restricted_columns
    )

    prompt = TextToSQLEngine.create_sql_prompt(
        user_query=payload.query,
        schema_context=schema_context,
        user_id=payload.user_id,
        user_role=payload.user_role or "user",
        dialect=payload.dialect or "postgres"
    )

    llm_resp = await LLMGateway.complete(
        messages=[
            {"role": "system", "content": "You are a strict read-only SQL generator. Output ONLY a SELECT SQL query in a ```sql block."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )

    try:
        sanitized_sql, params = TextToSQLEngine.extract_and_validate(
            raw_llm_response=llm_resp,
            allowed_tables=allowed_tables,
            allowed_columns=allowed_columns,
            dialect=payload.dialect or "postgres"
        )
        return {
            "status": "success",
            "guardrail_blocked": False,
            "sql_query": sanitized_sql,
            "parameters": params,
            "schema_tables": list(allowed_tables)
        }
    except Exception as err:
        return {
            "status": "error",
            "message": f"Query validation failed: {str(err)}",
            "sql_query": None
        }


@router.post("/format-sql-response", status_code=status.HTTP_200_OK)
async def format_sql_response_from_client_bridge(payload: FormatSQLResponseRequest, db: AsyncSession = Depends(get_db)):
    """
    Takes the raw execution output from the client's local database bridge
    and synthesizes an intuitive, natural language response for the end user.
    """
    stmt = select(Agent).where(Agent.id == payload.agent_id)
    res = await db.execute(stmt)
    agent = res.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")

    synth_prompt = f"""You are an enterprise AI assistant. Convert the following database results into a helpful, natural, and concise answer for the user.
Format the answer cleanly without decorative markdown asterisks (no '***' or '---').

User Question: {payload.query}
SQL Executed: {payload.sql_query}
Database Results:
{json.dumps(payload.db_results, default=str)}

Respond clearly, naturally, and concisely."""

    formatted_answer = await LLMGateway.complete(
        messages=[
            {"role": "system", "content": "You are an enterprise assistant synthesizing database records into natural language."},
            {"role": "user", "content": synth_prompt}
        ],
        temperature=0.3
    )

    return {
        "status": "success",
        "answer": formatted_answer
    }


from app.services.escalation.webhook_service import WebhookService
from app.services.escalation.email_service import EmailService


class EscalateRequest(BaseModel):
    session_id: str = Field(..., description="Active chat session ID")
    reason: Optional[str] = Field(default="User requested human support agent", description="Reason for escalation")
    user_contact: Optional[str] = Field(default=None, description="Email or phone number of user")
    user_query: Optional[str] = Field(default="", description="Latest inquiry or context")
    webhook_url: Optional[str] = Field(default=None, description="Optional custom webhook URL (Slack / Discord / HTTP)")
    email: Optional[str] = Field(default=None, description="Optional custom recipient email")


@router.post("/escalate", status_code=status.HTTP_200_OK)
async def escalate_to_human(payload: EscalateRequest, db: AsyncSession = Depends(get_db)):
    """
    Escalates a chat session to human support.
    1. Flags the session as escalated in the DB for the In-Studio Live Support Inbox.
    2. Dispatches real-time email notifications if configured.
    3. Dispatches Slack/Discord/CRM webhook alerts if configured.
    """
    stmt = select(ChatSession).where(ChatSession.id == payload.session_id)
    res = await db.execute(stmt)
    session = res.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    agent_name = "AI Assistant"
    webhook_url = payload.webhook_url
    escalation_email = payload.email
    custom_support_msg = None

    if session.agent_id:
        agent = await db.get(Agent, session.agent_id)
        if agent:
            agent_name = agent.name
            if agent.guardrail_config:
                try:
                    gc = json.loads(agent.guardrail_config)
                    if not webhook_url:
                        webhook_url = gc.get("escalation_webhook_url")
                    if not escalation_email:
                        escalation_email = gc.get("escalation_email")
                    if gc.get("support_contact_email") or gc.get("support_contact_phone"):
                        parts = []
                        if gc.get("support_contact_email"):
                            parts.append(f"Email: {gc.get('support_contact_email')}")
                        if gc.get("support_contact_phone"):
                            parts.append(f"Phone: {gc.get('support_contact_phone')}")
                        custom_support_msg = " Direct contact: " + " | ".join(parts)
                except Exception:
                    pass

    # Flag session in DB for Live Support Inbox
    session.is_escalated = True
    session.escalation_reason = payload.reason or "Live Support Request"
    session.escalation_contact = payload.user_contact or session.external_user_id or "Anonymous Visitor"
    session.is_resolved = False

    # Build assistant confirmation message
    conf_text = "I have connected your request to our support team. A representative has been notified and will review this conversation shortly."
    if custom_support_msg:
        conf_text += custom_support_msg

    asst_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=conf_text,
        metadata_json={"escalated": True, "reason": payload.reason}
    )
    db.add(asst_msg)
    await db.commit()

    # 1. Dispatch Webhook if configured
    webhook_res = None
    if webhook_url and webhook_url.strip():
        webhook_res = await WebhookService.send_escalation_alert(
            webhook_url=webhook_url.strip(),
            session_id=session.id,
            agent_name=agent_name,
            user_query=payload.user_query or "Human agent requested",
            reason=payload.reason or "Live Support Request",
            user_contact=session.escalation_contact
        )

    # 2. Dispatch Email Alert if configured
    email_res = None
    if escalation_email and escalation_email.strip():
        email_res = await EmailService.send_escalation_email(
            to_email=escalation_email.strip(),
            agent_name=agent_name,
            session_id=session.id,
            user_query=payload.user_query or "Human agent requested",
            reason=payload.reason or "Live Support Request",
            user_contact=session.escalation_contact
        )

    return {
        "status": "success",
        "message": "Session escalated to human support successfully.",
        "session_id": session.id,
        "is_escalated": True,
        "webhook_status": webhook_res,
        "email_status": email_res
    }


class TestWebhookRequest(BaseModel):
    webhook_url: str = Field(..., description="Slack, Discord, or Custom Webhook URL to test")
    agent_name: Optional[str] = Field(default="Live Agent Preview", description="Name of the Agent")


@router.post("/test-webhook", status_code=status.HTTP_200_OK)
async def test_escalation_webhook(payload: TestWebhookRequest):
    """
    Tests sending a mock escalation alert to a Slack, Discord, or custom Webhook URL.
    """
    if not payload.webhook_url or not payload.webhook_url.strip():
        raise HTTPException(status_code=400, detail="Webhook URL cannot be empty.")

    res = await WebhookService.send_escalation_alert(
        webhook_url=payload.webhook_url.strip(),
        session_id="test-session-ping",
        agent_name=payload.agent_name or "Live Support Preview",
        user_query="This is a test notification from the Plug-N-Play AI Studio to verify your webhook configuration.",
        reason="⚡ Admin Webhook Verification Ping",
        user_contact="admin-preview@client.com"
    )
    return res



