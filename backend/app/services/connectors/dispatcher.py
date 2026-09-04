import time
import json
import httpx
import logging
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.security import generate_connector_signature

logger = logging.getLogger(__name__)


class ConnectorDispatcher:
    """
    Manages secure outbound communication from Plug-N-Play Cloud
    to the Client's installed Connector service.
    """

    def __init__(self, endpoint_url: str, shared_secret: str, timeout: float = settings.CONNECTOR_TIMEOUT_SECONDS):
        self.endpoint_url = endpoint_url.rstrip("/")
        self.shared_secret = shared_secret
        self.timeout = timeout

    def _prepare_headers(self, body_bytes: bytes) -> Dict[str, str]:
        timestamp = str(int(time.time()))
        signature = generate_connector_signature(self.shared_secret, timestamp, body_bytes)
        return {
            "Content-Type": "application/json",
            "X-PNP-Timestamp": timestamp,
            "X-PNP-Signature": signature
        }

    async def check_health(self) -> bool:
        """Ping the client connector health endpoint."""
        url = f"{self.endpoint_url}/health"
        body_bytes = b"{}"
        headers = self._prepare_headers(body_bytes)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, content=body_bytes, headers=headers)
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed health check for connector {self.endpoint_url}: {e}")
            return False

    async def fetch_schema(self) -> Dict[str, Any]:
        """Request whitelisted tables and column schemas from the client connector."""
        url = f"{self.endpoint_url}/schema"
        body_bytes = b"{}"
        headers = self._prepare_headers(body_bytes)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, content=body_bytes, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Connector schema fetch failed ({resp.status_code}): {resp.text}")
            return resp.json()

    async def execute_sql(
        self, 
        sql: str, 
        params: Optional[Dict[str, Any]] = None, 
        max_rows: int = settings.CONNECTOR_MAX_ROWS
    ) -> List[Dict[str, Any]]:
        """
        Send a verified, read-only SQL query with bound parameters to the client connector.
        Returns tabular records as a list of dictionaries.
        """
        url = f"{self.endpoint_url}/execute-sql"
        payload = {
            "sql": sql,
            "params": params or {},
            "max_rows": max_rows
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        headers = self._prepare_headers(body_bytes)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, content=body_bytes, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Connector SQL execution failed ({resp.status_code}): {resp.text}")
            
            data = resp.json()
            return data.get("rows", [])
