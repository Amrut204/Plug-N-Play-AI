import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat import ChatMessage
from app.services.llm.gateway import LLMGateway

logger = logging.getLogger(__name__)


class QueryContextualizer:
    """
    Reformulates follow-up queries into standalone, search-ready queries
    using recent conversation history.
    """

    CONTEXTUAL_TRIGGERS = {
        "he", "she", "it", "they", "his", "her", "their", "him", "them",
        "this", "that", "these", "those", "what about", "how about",
        "and", "too", "also", "compare", "why", "who", "which", "where",
        "more", "details", "cabin", "room", "phone", "email", "salary",
        "marks", "attendance", "previous", "earlier", "same"
    }

    @classmethod
    async def contextualize_query(
        cls,
        db: AsyncSession,
        session_id: str,
        current_query: str,
        max_history_turns: int = 4
    ) -> str:
        """
        Takes current query and recent chat history to produce a standalone query.
        """
        if not current_query or not current_query.strip():
            return current_query

        # 1. Fetch recent messages
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(max_history_turns * 2)
        )
        res = await db.execute(stmt)
        messages: List[ChatMessage] = list(reversed(res.scalars().all()))

        # Filter out the current turn if it was just saved
        history_msgs = [m for m in messages if m.content.strip() != current_query.strip()]
        if not history_msgs:
            return current_query

        # 2. Heuristic check: does query need contextualization?
        q_words = set(current_query.lower().strip().split())
        has_trigger = bool(cls.CONTEXTUAL_TRIGGERS.intersection(q_words)) or len(q_words) <= 4

        if not has_trigger:
            return current_query

        # 3. Format history turns
        history_text = "\n".join([
            f"{m.role.capitalize()}: {m.content[:200]}"
            for m in history_msgs[-6:]
        ])

        system_prompt = (
            "You are a Search Query Contextualizer. Given a conversation history and a user follow-up query, "
            "reformulate the follow-up query into a standalone, self-contained search query. "
            "Resolve all pronouns (he, she, it, his, her, that, etc.) using the entities mentioned in the history. "
            "Output ONLY the standalone query text without quotes, commentary, or answers."
        )

        user_prompt = (
            f"Conversation History:\n{history_text}\n\n"
            f"User Follow-up Query: \"{current_query}\"\n\n"
            "Standalone Query:"
        )

        try:
            standalone = await LLMGateway.complete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="qwen/qwen3.8-27b",
                temperature=0.0,
                max_tokens=80
            )
            cleaned = standalone.strip().strip('"').strip("'")
            if cleaned and len(cleaned) > 2:
                logger.info(f"Query Contextualized: '{current_query}' -> '{cleaned}'")
                return cleaned
        except Exception as e:
            logger.warning(f"Query contextualization failed: {e}. Using original query.")

        return current_query
