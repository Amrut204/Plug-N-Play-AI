from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, Any
from app.core.database import get_db
from app.models.chat import QueryLog, ChatMessage, ChatSession

router = APIRouter(prefix="/analytics", tags=["Analytics & Telemetry"])


@router.get("/{tenant_id}/overview")
async def get_analytics_overview(tenant_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve operational telemetry, query route breakdown, and user satisfaction (CSAT) for a tenant."""
    # Total queries
    stmt_total = select(func.count(QueryLog.id)).where(QueryLog.tenant_id == tenant_id)
    res_total = await db.execute(stmt_total)
    total_queries = res_total.scalar() or 0

    # Route breakdown
    stmt_routes = (
        select(QueryLog.route_chosen, func.count(QueryLog.id))
        .where(QueryLog.tenant_id == tenant_id)
        .group_by(QueryLog.route_chosen)
    )
    res_routes = await db.execute(stmt_routes)
    route_breakdown = {row[0]: row[1] for row in res_routes.all()}

    # Blocked queries count
    blocked_count = route_breakdown.get("GUARDRAIL_BLOCKED", 0) + route_breakdown.get("POLICY_BLOCKED", 0)

    # Average latencies
    stmt_latencies = (
        select(
            func.avg(QueryLog.sql_execution_ms),
            func.avg(QueryLog.rag_retrieval_ms),
            func.avg(QueryLog.llm_generation_ms)
        )
        .where(QueryLog.tenant_id == tenant_id)
    )
    res_latencies = await db.execute(stmt_latencies)
    avg_sql, avg_rag, avg_llm = res_latencies.one()

    # User Feedback (CSAT)
    feedback_stmt = (
        select(ChatMessage.feedback_rating, func.count(ChatMessage.id))
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(ChatSession.tenant_id == tenant_id, ChatMessage.feedback_rating.isnot(None))
        .group_by(ChatMessage.feedback_rating)
    )
    res_feedback = await db.execute(feedback_stmt)
    feedback_counts = {row[0]: row[1] for row in res_feedback.all()}

    thumbs_up = feedback_counts.get(1, 0)
    thumbs_down = feedback_counts.get(-1, 0)
    total_feedback = thumbs_up + thumbs_down
    csat_percentage = round((thumbs_up / total_feedback) * 100, 1) if total_feedback > 0 else 100.0

    return {
        "tenant_id": tenant_id,
        "total_queries": total_queries,
        "blocked_queries": blocked_count,
        "csat_score": csat_percentage,
        "total_feedback_count": total_feedback,
        "feedback_breakdown": {
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down
        },
        "routes": route_breakdown,
        "avg_latencies_ms": {
            "sql": round(avg_sql or 0, 1),
            "rag": round(avg_rag or 0, 1),
            "llm": round(avg_llm or 0, 1)
        }
    }


@router.get("/{tenant_id}/recent-logs")
async def get_recent_query_logs(tenant_id: str, limit: int = 15, db: AsyncSession = Depends(get_db)):
    """Retrieve recent query executions with telemetry and routing details."""
    stmt = (
        select(QueryLog)
        .where(QueryLog.tenant_id == tenant_id)
        .order_by(QueryLog.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "query_text": log.user_query,
            "route_chosen": log.route_chosen,
            "sql_ms": log.sql_execution_ms,
            "rag_ms": log.rag_retrieval_ms,
            "llm_ms": log.llm_generation_ms,
            "total_ms": round((log.sql_execution_ms or 0) + (log.rag_retrieval_ms or 0) + (log.llm_generation_ms or 0), 1),
            "created_at": log.created_at.isoformat() if log.created_at else None
        }
        for log in logs
    ]
