import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import List, Dict, Any
from app.core.database import get_db
from app.models.agents import Agent
from app.models.tenants import Tenant
from app.models.chat import ChatSession
from app.models.rag import RAGSource
from app.schemas.agents import AgentCreate, AgentResponse, AgentUpdate

router = APIRouter(prefix="/agents", tags=["AI Agents"])


@router.post("/{tenant_id}", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(tenant_id: str, payload: AgentCreate, db: AsyncSession = Depends(get_db)):
    """Create a new AI Agent for a tenant."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Tenant not found.")

    agent = Agent(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        system_prompt=payload.system_prompt,
        model_provider=payload.model_provider,
        model_name=payload.model_name,
        temperature=payload.temperature
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/{tenant_id}", response_model=List[AgentResponse])
async def list_agents(tenant_id: str, db: AsyncSession = Depends(get_db)):
    """List all AI Agents for a tenant."""
    stmt = select(Agent).where(Agent.tenant_id == tenant_id).order_by(Agent.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/tenant/{tenant_id}/detailed")
async def list_agents_detailed(tenant_id: str, db: AsyncSession = Depends(get_db)) -> List[Dict[str, Any]]:
    """List all AI Agents for a tenant with rich telemetry (session counts, docs count, audience)."""
    stmt = select(Agent).where(Agent.tenant_id == tenant_id).order_by(Agent.created_at.desc())
    result = await db.execute(stmt)
    agents = result.scalars().all()

    # Batch count sessions for all agents of this tenant
    s_stmt = (
        select(ChatSession.agent_id, func.count(ChatSession.id))
        .where(ChatSession.tenant_id == tenant_id)
        .group_by(ChatSession.agent_id)
    )
    s_res = await db.execute(s_stmt)
    sess_counts = dict(s_res.all())

    # Batch count documents for all agents of this tenant
    d_stmt = (
        select(RAGSource.agent_id, func.count(RAGSource.id))
        .where(RAGSource.tenant_id == tenant_id)
        .group_by(RAGSource.agent_id)
    )
    d_res = await db.execute(d_stmt)
    docs_counts = dict(d_res.all())

    detailed = []
    for ag in agents:
        sess_count = sess_counts.get(ag.id, 0)
        docs_count = docs_counts.get(ag.id, 0)

        # Extract audience & service type
        target_aud = "end_user"
        svc_type = "hybrid"
        if ag.description:
            desc_up = ag.description.upper()
            if "RAG" in desc_up and "HYBRID" not in desc_up and "SQL" not in desc_up:
                svc_type = "rag"
            elif "SQL" in desc_up and "HYBRID" not in desc_up:
                svc_type = "sql"

        webhook_url = None
        if ag.guardrail_config:
            try:
                g_cfg = json.loads(ag.guardrail_config)
                if isinstance(g_cfg, dict):
                    target_aud = g_cfg.get("target_audience", "end_user")
                    webhook_url = g_cfg.get("escalation_webhook_url")
            except Exception:
                pass

        detailed.append({
            "id": ag.id,
            "tenant_id": ag.tenant_id,
            "name": ag.name,
            "description": ag.description,
            "service_type": svc_type,
            "target_audience": target_aud,
            "model_provider": ag.model_provider,
            "model_name": ag.model_name,
            "system_prompt": ag.system_prompt,
            "is_active": ag.is_active,
            "session_count": sess_count,
            "docs_count": docs_count,
            "has_guardrails": bool(ag.guardrail_config),
            "escalation_webhook_url": webhook_url,
            "created_at": ag.created_at.isoformat() if ag.created_at else None
        })

    return detailed


@router.delete("/{agent_id}", status_code=status.HTTP_200_OK)
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an agent by ID."""
    stmt = select(Agent).where(Agent.id == agent_id)
    res = await db.execute(stmt)
    agent = res.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")

    await db.delete(agent)
    await db.commit()
    return {"status": "success", "message": f"Agent {agent_id} deleted."}


@router.patch("/{agent_id}")
async def update_agent(agent_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """Update agent details including name, description, system_prompt, active status, and escalation webhook."""
    stmt = select(Agent).where(Agent.id == agent_id)
    res = await db.execute(stmt)
    agent = res.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")

    if "name" in payload and payload["name"]:
        agent.name = payload["name"]
    if "description" in payload:
        agent.description = payload["description"]
    if "system_prompt" in payload:
        agent.system_prompt = payload["system_prompt"]
    if "is_active" in payload:
        agent.is_active = bool(payload["is_active"])

    if "escalation_webhook_url" in payload:
        gc = {}
        if agent.guardrail_config:
            try:
                gc = json.loads(agent.guardrail_config)
            except Exception:
                gc = {}
        gc["escalation_webhook_url"] = (payload["escalation_webhook_url"] or "").strip()
        agent.guardrail_config = json.dumps(gc)

    await db.commit()
    await db.refresh(agent)
    return {
        "status": "success", 
        "agent": {
            "id": agent.id, 
            "name": agent.name, 
            "description": agent.description,
            "is_active": agent.is_active,
            "guardrail_config": agent.guardrail_config
        }
    }
