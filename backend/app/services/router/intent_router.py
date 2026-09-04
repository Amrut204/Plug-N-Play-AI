import json
import logging
from typing import Dict, Any, Tuple
from app.services.llm.gateway import LLMGateway

logger = logging.getLogger(__name__)


class IntentRouter:
    """
    Intelligent Intent Router classifying queries into SQL, RAG, HYBRID, or DIRECT.
    """

    ROUTER_SYSTEM_PROMPT = """You are the central query router for an enterprise AI data layer.
Classify the user query into exactly ONE of the following intents:
1. "RAG": For questions about policies, returns, refunds, warranties, shipping, handbooks, guidelines, terms, regulations, FAQs, instructions, or descriptive knowledge.
2. "SQL": For questions querying structured database records (e.g. specific order status, stock counts, product catalog prices, student grades, user profile details).
3. "HYBRID": For questions that compare a user's live personal record with an institutional rule or policy (e.g., "Am I eligible for scholarship?", "Can I sit for exam given my attendance?", "Can I return this product?").
4. "DIRECT": For casual greetings, thanks, or general clarifications not needing data.

Respond in strict JSON format:
{
  "intent": "SQL" | "RAG" | "HYBRID" | "DIRECT",
  "reason": "<short explanation>"
}"""

    @classmethod
    async def route_query(cls, user_query: str) -> Tuple[str, str]:
        """
        Returns (intent, reason) with fast heuristic check first to save LLM tokens.
        """
        q_lower = user_query.lower().strip()

        # 1. Fast Zero-Token Heuristic Match based on structural query patterns
        if any(w in q_lower for w in ["can i ", "am i eligible", "do i qualify", "am i allowed", "can i return", "is it possible for me"]):
            return "HYBRID", "Heuristic detected combined status and policy evaluation"
        elif any(w in q_lower for w in [
            "policy", "policies", "rule", "rules", "guideline", "guidelines", "regulation", "regulations", 
            "handbook", "criteria", "terms", "condition", "conditions", "faq", "faqs", "return", "returns", 
            "refund", "refunds", "exchange", "exchanges", "window", "shipping", "delivery", "warranty", 
            "warranties", "cancel", "cancellation", "curfew", "night out", "attendance requirement", 
            "debarred", "condonation", "procedure", "how do i", "how can i", "what is the process", 
            "return window", "refund policy", "shipping policy", "how much days", "how many days", "how long"
        ]):
            return "RAG", "Heuristic detected knowledge/document/policy inquiry"
        elif any(q_lower.startswith(g) for g in ["hi", "hello", "hey", "who are you", "help", "good morning", "good evening"]):
            return "DIRECT", "General greeting"
        elif any(w in q_lower for w in [
            "how many", "count", "list", "show", "total", "who is", "what is", "is there", 
            "where is", "find", "search", "get", "give me", "which", "filter", "sum", "average", "avg", "top", "price of", "stock"
        ]):
            return "SQL", "Heuristic detected structured data query"

        # 2. LLM-based Intent Routing with minimal token budget
        messages = [
            {"role": "system", "content": cls.ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Classify the intent for this query:\n\n{user_query}"}
        ]

        try:
            response = await LLMGateway.complete(messages, temperature=0.0, max_tokens=30)
            clean_resp = response.strip()
            if "```json" in clean_resp:
                clean_resp = clean_resp.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_resp:
                clean_resp = clean_resp.split("```")[1].split("```")[0].strip()

            parsed = json.loads(clean_resp)
            intent = parsed.get("intent", "RAG").upper()
            if intent not in {"SQL", "RAG", "HYBRID", "DIRECT"}:
                intent = "RAG"
            return intent, parsed.get("reason", "")
        except Exception as e:
            logger.warning(f"Intent routing fallback triggered: {e}")
            return "RAG", "Defaulting to RAG route for query"

