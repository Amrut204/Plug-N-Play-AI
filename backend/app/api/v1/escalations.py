from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.chat import ChatSession, ChatMessage
from app.models.agents import Agent
from app.models.tenants import Tenant
from app.services.escalation.email_service import EmailService

router = APIRouter(prefix="/escalations", tags=["Escalations & Support"])


class TestEmailRequest(BaseModel):
    email: str = Field(..., description="Target email address to receive escalation alerts")
    agent_name: Optional[str] = Field(default="Live Support Preview", description="Agent Name")


@router.get("/tenant/{tenant_id}")
async def list_tenant_escalations(tenant_id: str, db: AsyncSession = Depends(get_db)):
    """
    List all human escalation tickets and support requests for a tenant.
    """
    stmt = (
        select(ChatSession)
        .where(ChatSession.tenant_id == tenant_id, ChatSession.is_escalated == True)
        .order_by(desc(ChatSession.created_at))
    )
    res = await db.execute(stmt)
    sessions = res.scalars().all()

    escalations = []
    pending_count = 0
    resolved_count = 0

    for s in sessions:
        if s.is_resolved:
            resolved_count += 1
        else:
            pending_count += 1

        agent = await db.get(Agent, s.agent_id) if s.agent_id else None

        # Fetch messages for this session
        m_stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == s.id)
            .order_by(ChatMessage.created_at.asc())
        )
        m_res = await db.execute(m_stmt)
        messages = m_res.scalars().all()

        last_user_query = ""
        for m in reversed(messages):
            if m.role == "user":
                last_user_query = m.content
                break

        escalations.append({
            "session_id": s.id,
            "agent_id": s.agent_id,
            "agent_name": agent.name if agent else "AI Assistant",
            "external_user_id": s.external_user_id or "Anonymous Visitor",
            "escalation_contact": s.escalation_contact or s.external_user_id or "Not provided",
            "escalation_reason": s.escalation_reason or "User clicked Live Support",
            "is_resolved": bool(s.is_resolved),
            "resolved_at": s.resolved_at.isoformat() if s.resolved_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "last_user_query": last_user_query,
            "message_count": len(messages),
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "feedback": m.feedback_rating,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in messages
            ]
        })

    return {
        "tenant_id": tenant_id,
        "total": len(escalations),
        "pending": pending_count,
        "resolved": resolved_count,
        "escalations": escalations
    }


@router.post("/{session_id}/resolve")
async def resolve_escalation(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Mark an escalated chat session as resolved.
    """
    stmt = select(ChatSession).where(ChatSession.id == session_id)
    res = await db.execute(stmt)
    session = res.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    session.is_resolved = True
    session.resolved_at = datetime.now(timezone.utc)

    # Add resolution note message
    res_msg = ChatMessage(
        session_id=session.id,
        role="system",
        content="Support ticket marked as resolved by management.",
        metadata_json={"resolved": True}
    )
    db.add(res_msg)
    await db.commit()

    return {
        "status": "success",
        "message": f"Escalation for session {session_id} marked as resolved.",
        "resolved_at": session.resolved_at.isoformat()
    }


@router.post("/test-email")
async def test_escalation_email(payload: TestEmailRequest):
    """
    Test sending a sample escalation notification email.
    """
    if not payload.email or "@" not in payload.email:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    res = await EmailService.send_escalation_email(
        to_email=payload.email,
        agent_name=payload.agent_name or "Live Support Preview",
        session_id="test-session-email-preview",
        user_query="This is a test notification to verify your support escalation email setup.",
        reason="⚡ Admin Email Verification Ping",
        user_contact="customer-preview@client.com"
    )
    return res
