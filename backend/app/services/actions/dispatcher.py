import time
import json
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.actions import ActionDefinition, ActionExecutionLog
from app.schemas.actions import ActionExecuteResponse
from app.services.llm.gateway import LLMGateway

logger = logging.getLogger(__name__)


class ActionDispatcher:
    """
    Handles cryptographic signing, webhook dispatching to client backends,
    audit logging, and natural language response synthesis.
    """

    @classmethod
    def compute_signature(cls, secret: str, timestamp: str, payload_str: str) -> str:
        """Computes HMAC-SHA256 signature to authenticate the request on the client backend."""
        message = f"{timestamp}.{payload_str}".encode("utf-8")
        return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    @classmethod
    async def dispatch_action(
        cls,
        action: ActionDefinition,
        parameters: Dict[str, Any],
        tenant_id: str,
        external_user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        shared_secret: Optional[str] = None,
        agent_name: str = "Plug-N-Play AI"
    ) -> ActionExecuteResponse:
        # Safeguard: disallow execution of banking or sensitive financial actions
        act_check = f"{action.name.lower()} {action.display_name.lower()} {action.endpoint_url.lower()}"
        if any(k in act_check for k in ["freeze_card", "freeze_debit", "freeze_credit", "transfer_fund", "bank_transfer", "withdraw_cash", "credit_card", "lock_card"]):
            return ActionExecuteResponse(
                success=False,
                action_id=action.id,
                action_name=action.name,
                response_status=403,
                execution_time_ms=0,
                message="Action blocked by security policy: Autonomous execution of banking and financial card operations is restricted. Please use official verified banking portals or human support."
            )

        start_time = time.perf_counter()
        secret = shared_secret or f"pnp_secret_{tenant_id}"
        timestamp = str(int(time.time()))
        
        # Enforce external_user_id in payload if present
        payload = dict(parameters)
        if external_user_id and "user_id" not in payload and "external_user_id" not in payload:
            payload["user_id"] = external_user_id

        payload_str = json.dumps(payload, default=str)
        signature = cls.compute_signature(secret, timestamp, payload_str)

        headers = {
            "Content-Type": "application/json",
            "x-pnp-signature": signature,
            "x-pnp-timestamp": timestamp,
            "x-pnp-tenant-id": tenant_id,
            "x-pnp-action-id": action.id,
            "x-pnp-user-id": external_user_id or ""
        }

        status_code = 500
        raw_response_text = ""
        response_json = None
        is_success = False

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                method = (action.http_method or "POST").upper()
                if method == "PUT":
                    res = await client.put(action.endpoint_url, headers=headers, content=payload_str)
                elif method == "PATCH":
                    res = await client.patch(action.endpoint_url, headers=headers, content=payload_str)
                else:
                    res = await client.post(action.endpoint_url, headers=headers, content=payload_str)

                status_code = res.status_code
                raw_response_text = res.text
                if 200 <= status_code < 300:
                    is_success = True
                    try:
                        response_json = res.json()
                    except Exception:
                        response_json = {"raw": raw_response_text}
                else:
                    logger.warning(f"Action {action.name} returned HTTP {status_code}: {raw_response_text}")

        except httpx.TimeoutException:
            status_code = 504
            raw_response_text = "Connection timed out after 15 seconds."
            logger.error(f"Timeout dispatching action {action.name} to {action.endpoint_url}")
        except Exception as exc:
            status_code = 500
            raw_response_text = f"Network dispatch error: {str(exc)}"
            logger.error(f"Error dispatching action {action.name}: {exc}")

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # Record audit log if db session provided
        if db:
            try:
                log_entry = ActionExecutionLog(
                    tenant_id=tenant_id,
                    action_id=action.id,
                    session_id=session_id,
                    external_user_id=external_user_id,
                    parameters_payload=payload,
                    response_status=status_code,
                    response_body=raw_response_text[:3000],
                    execution_time_ms=latency_ms
                )
                db.add(log_entry)
                await db.commit()
            except Exception as log_err:
                logger.error(f"Failed to record action execution log: {log_err}")

        # Synthesize authoritative BLUF confirmation message
        natural_confirmation = await cls._synthesize_confirmation(
            agent_name=agent_name,
            action=action,
            is_success=is_success,
            response_json=response_json,
            raw_text=raw_response_text,
            parameters=payload
        )

        return ActionExecuteResponse(
            status="success" if is_success else "failed",
            action_name=action.name,
            display_name=action.display_name,
            response_data=response_json,
            error_message=None if is_success else raw_response_text,
            natural_confirmation=natural_confirmation,
            execution_time_ms=latency_ms
        )

    @classmethod
    async def _synthesize_confirmation(
        cls,
        agent_name: str,
        action: ActionDefinition,
        is_success: bool,
        response_json: Optional[Dict[str, Any]],
        raw_text: str,
        parameters: Dict[str, Any]
    ) -> str:
        """Synthesizes a confident executive confirmation or explanatory error message."""
        if is_success:
            details_str = json.dumps(response_json or parameters, default=str)
            system_prompt = f"""You are the official AI assistant representing {agent_name}.
A user action '{action.display_name}' was successfully executed on the client system.

CORE RESPONSE RULES:
1. CONFIDENT & DIRECT (ZERO HEDGING): State the outcome decisively in sentence 1 (Bottom Line Up Front).
2. HIGHLIGHT DETAILS: Bold any reference IDs, confirmation numbers, dates, or refund amounts.
3. NEXT STEPS: In sentence 2, clearly state the next action or expected timeline.
4. Keep the entire response under 3 sentences. No conversational filler or apologetic preambles."""

            user_prompt = f"Action: {action.display_name}\nTarget Parameters: {json.dumps(parameters)}\nClient Result: {details_str}"
            try:
                conf = await LLMGateway.complete(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=200
                )
                if conf and len(conf.strip()) > 10:
                    return conf.strip()
            except Exception:
                pass

            # Fallback deterministic template
            ref = ""
            if response_json and isinstance(response_json, dict):
                for k in ["id", "reference_id", "confirmation_id", "cancellation_id", "booking_id", "ref"]:
                    if k in response_json:
                        ref = f" (Reference: **{response_json[k]}**)"
                        break
            return f"Your request for **{action.display_name}** has been completed successfully{ref}. All corresponding records have been updated."

        else:
            # Handle failure decisively
            return f"I was unable to complete your request for **{action.display_name}**. The system reported: {raw_text[:200]}. Please contact support or try again later."
