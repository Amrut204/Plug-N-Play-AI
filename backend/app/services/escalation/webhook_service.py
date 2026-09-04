import logging
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class WebhookService:
    """
    Dispatches real-time human escalation notifications to Slack, Discord, or Custom Webhook URLs.
    """

    @classmethod
    async def send_escalation_alert(
        cls,
        webhook_url: str,
        session_id: str,
        agent_name: str,
        user_query: str,
        reason: str = "User requested live human agent",
        user_contact: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dispatches an escalation event to the configured webhook endpoint.
        Auto-formats payload for Slack blocks, Discord embeds, or standard JSON.
        """
        if not webhook_url or not webhook_url.strip():
            logger.info("No webhook URL configured; skipping external notification.")
            return {"status": "skipped", "message": "No webhook URL configured"}

        url = webhook_url.strip()
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # 1. Format Payload based on Webhook Type
        if "slack.com" in url:
            payload = {
                "text": f"🚨 *Live Human Agent Escalation* | Agent: *{agent_name}*",
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": "🚨 Human Support Requested"}
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Agent:*\n{agent_name}"},
                            {"type": "mrkdwn", "text": f"*Session ID:*\n`{session_id}`"},
                            {"type": "mrkdwn", "text": f"*Time:*\n{now_str}"},
                            {"type": "mrkdwn", "text": f"*User Contact:*\n{user_contact or 'Anonymous'}"}
                        ]
                    },
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": f"*Reason:*\n_{reason}_\n\n*Latest User Query:*\n> {user_query}"}
                    }
                ]
            }
        elif "discord.com" in url:
            payload = {
                "content": f"🚨 **Live Human Agent Escalation** from `{agent_name}`",
                "embeds": [
                    {
                        "title": "Human Support Escalation Triggered",
                        "color": 15158332,  # Crimson Red
                        "fields": [
                            {"name": "Agent", "value": agent_name, "inline": True},
                            {"name": "Session ID", "value": f"`{session_id}`", "inline": True},
                            {"name": "User Contact", "value": user_contact or "Anonymous", "inline": True},
                            {"name": "Reason", "value": reason, "inline": False},
                            {"name": "Latest Query", "value": f"```{user_query}```", "inline": False}
                        ],
                        "footer": {"text": f"Plug-N-Play AI • {now_str}"}
                    }
                ]
            }
        else:
            # Standard Generic REST Webhook
            payload = {
                "event": "human_escalation",
                "timestamp": now_str,
                "agent_name": agent_name,
                "session_id": session_id,
                "reason": reason,
                "user_query": user_query,
                "user_contact": user_contact
            }

        # 2. Dispatch HTTP POST
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code < 400:
                    logger.info(f"Escalation webhook dispatched successfully to {url} (status: {res.status_code})")
                    return {"status": "success", "http_status": res.status_code}
                else:
                    logger.warning(f"Escalation webhook responded with error {res.status_code}: {res.text}")
                    return {"status": "error", "http_status": res.status_code, "error": res.text}
        except Exception as e:
            logger.error(f"Failed to dispatch escalation webhook: {e}")
            return {"status": "error", "message": str(e)}
