import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.models.actions import ActionDefinition
from app.services.llm.gateway import LLMGateway

logger = logging.getLogger(__name__)


class ActionToolCompiler:
    """
    Compiles database ActionDefinition records into standard OpenAI / Groq
    Function Calling tool specifications for LLM reasoning and parameter extraction.
    Also provides high-precision action intent detection and parameter extraction.
    """

    @classmethod
    def compile_actions_to_tools(cls, actions: List[ActionDefinition]) -> List[Dict[str, Any]]:
        """Transforms a list of ActionDefinitions into LLM tool schemas."""
        tools = []
        for act in actions:
            if not act.is_active:
                continue

            properties = {}
            required = []
            
            raw_params = act.parameters_schema or []
            for p in raw_params:
                p_name = p.get("name")
                if not p_name:
                    continue
                p_type = p.get("type", "string").lower()
                if p_type not in ["string", "number", "integer", "boolean"]:
                    p_type = "string"

                properties[p_name] = {
                    "type": p_type,
                    "description": p.get("description", "")
                }
                if p.get("required", True):
                    required.append(p_name)

            tools.append({
                "type": "function",
                "function": {
                    "name": act.name,
                    "description": f"{act.display_name}: {act.description}",
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required
                    }
                }
            })

        return tools

    @classmethod
    async def detect_action_intent(
        cls,
        query: str,
        actions: List[ActionDefinition],
        user_role: str = "user"
    ) -> Optional[Tuple[ActionDefinition, Dict[str, Any]]]:
        """
        Detects if the user query triggers an explicit Action/Workflow execution request.
        Uses zero-token heuristic match first for common operational patterns,
        falling back to LLM JSON parameter extraction.
        """
        if not actions or not query:
            return None

        # Filter by active and role authorization
        available_actions = [
            a for a in actions 
            if a.is_active and (not a.allowed_roles or user_role in a.allowed_roles or "*" in a.allowed_roles)
        ]
        if not available_actions:
            return None

        q_lower = query.lower().strip()

        # Guard against purely informational / policy queries
        is_informational = any(q_lower.startswith(p) for p in [
            "what is", "what are", "how do i", "how can i", "how to", "why is", "tell me about", "is there a policy"
        ]) or any(p in q_lower for p in [
            "return policy", "refund policy", "cancellation policy", "attendance policy", 
            "how many days", "what is the window", "what are the rules"
        ])

        if not is_informational:
            # 1. Fast heuristic detection for common operational commands
            for act in available_actions:
                act_name_words = act.name.replace("_", " ").split()
                act_display_words = act.display_name.lower().split()
                
                pattern_found = False
                if any(w in q_lower for w in ["cancel", "refund"]) and "cancel" in act.name:
                    pattern_found = True
                elif any(w in q_lower for w in ["condonation", "appeal", "medical condonation"]) and ("condonation" in act.name or "appeal" in act.name):
                    pattern_found = True
                elif any(w in q_lower for w in ["appointment", "book appointment", "schedule"]) and ("appointment" in act.name or "book" in act.name):
                    pattern_found = True
                elif any(w in q_lower for w in ["ticket", "support ticket", "report issue", "helpdesk", "create ticket"]) and ("ticket" in act.name or "support" in act.name):
                    pattern_found = True
                elif all(w in q_lower for w in act_name_words):
                    pattern_found = True
                elif all(w in q_lower for w in act_display_words):
                    pattern_found = True

                if pattern_found:
                    extracted: Dict[str, Any] = {}
                    schema = act.parameters_schema or []
                    for param in schema:
                        p_name = param.get("name", "")
                        p_type = param.get("type", "string").lower()
                        # Extract numeric/alphanumeric IDs (e.g. order_id, student_id, card_id)
                        if any(id_key in p_name.lower() for id_key in ["order_id", "order", "id", "ref", "ticket", "number"]):
                            id_match = re.search(r"#?(\d{3,12})", query)
                            if id_match:
                                val = id_match.group(1)
                                extracted[p_name] = int(val) if p_type in ["integer", "number"] else val
                            else:
                                alphanumeric_match = re.search(r"#?([A-Za-z0-9_-]{4,25})", query)
                                if alphanumeric_match:
                                    extracted[p_name] = alphanumeric_match.group(1)
                        elif "reason" in p_name.lower():
                            reason_match = re.search(r"(?:because|due to|reason is|reason:)\s*([^.,\n]+)", query, re.IGNORECASE)
                            if reason_match:
                                extracted[p_name] = reason_match.group(1).strip()
                            else:
                                extracted[p_name] = "Customer requested cancellation via AI Assistant"
                        elif "date" in p_name.lower() or "time" in p_name.lower():
                            date_match = re.search(r"(tomorrow|next week|today|\d{4}-\d{2}-\d{2})", query, re.IGNORECASE)
                            if date_match:
                                extracted[p_name] = date_match.group(1)

                    required_params = [p.get("name") for p in schema if p.get("required", True)]
                    has_required = all(r in extracted for r in required_params)
                    if has_required or not required_params:
                        logger.info(f"Action fast heuristic detected: {act.name} with params {extracted}")
                        return act, extracted

        # 2. LLM-based Function/Action Intent Classification & Parameter Extraction
        action_descriptions = []
        for act in available_actions:
            action_descriptions.append({
                "name": act.name,
                "display_name": act.display_name,
                "description": act.description,
                "parameters_schema": act.parameters_schema
            })

        system_prompt = f"""You are an enterprise AI Action Intent Classifier.
Determine if the user query is an explicit command to TRIGGER or EXECUTE one of the registered actions.

REGISTERED ACTIONS:
{json.dumps(action_descriptions, indent=2)}

RULES:
1. ONLY match if the user wants the system to EXECUTE an action (e.g. "cancel order 123", "submit my appeal").
2. DO NOT match if the user is only asking for information, checking eligibility, or querying a policy (e.g. "What is the return policy?", "Can I return within 30 days?").
3. Extract all parameter values present in the user query according to each parameter's schema.
4. If matched, respond in strict JSON:
{{
  "matched": true,
  "action_name": "<name>",
  "parameters": {{ "<param_name>": <extracted_value> }},
  "confidence": 0.95
}}
5. If not matched, respond in strict JSON:
{{
  "matched": false
}}"""

        try:
            resp = await LLMGateway.complete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"User Query: {query}"}
                ],
                temperature=0.0,
                max_tokens=250
            )

            clean_resp = resp.strip()
            if "```json" in clean_resp:
                clean_resp = clean_resp.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_resp:
                clean_resp = clean_resp.split("```")[1].split("```")[0].strip()

            parsed = json.loads(clean_resp)
            if parsed.get("matched"):
                action_name = parsed.get("action_name", "")
                for act in available_actions:
                    if act.name.lower() == action_name.lower():
                        return act, parsed.get("parameters", {})
        except Exception as e:
            logger.warning(f"Action intent LLM classification fallback: {e}")

        return None
