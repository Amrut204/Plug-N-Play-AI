from fastapi import APIRouter, Request, HTTPException, Header, status
from typing import List, Dict, Any, Optional
from plug_n_play_connector.security import verify_hmac_signature
from plug_n_play_connector.handlers import TableSchema, BaseExecutor
import json


def create_connector_router(
    shared_secret: str,
    executor: BaseExecutor,
    tables: List[TableSchema]
) -> APIRouter:
    """
    Creates a pre-configured, authenticated FastAPI APIRouter that the client application
    mounts to expose the standardized Plug-N-Play AI Connector endpoints.
    """
    router = APIRouter()

    async def _authenticate_request(request: Request, x_pnp_timestamp: str, x_pnp_signature: str) -> bytes:
        body = await request.body()
        is_valid, reason = verify_hmac_signature(
            secret=shared_secret,
            timestamp=x_pnp_timestamp,
            body=body,
            received_signature=x_pnp_signature
        )
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Connector Auth Failed: {reason}")
        return body

    @router.post("/health")
    async def health_check(
        request: Request,
        x_pnp_timestamp: Optional[str] = Header(None),
        x_pnp_signature: Optional[str] = Header(None)
    ):
        await _authenticate_request(request, x_pnp_timestamp or "0", x_pnp_signature or "")
        return {"status": "connected", "service": "Plug-N-Play Client Connector"}

    @router.post("/schema")
    async def get_schema(
        request: Request,
        x_pnp_timestamp: Optional[str] = Header(None),
        x_pnp_signature: Optional[str] = Header(None)
    ):
        await _authenticate_request(request, x_pnp_timestamp or "0", x_pnp_signature or "")
        return {
            "tables": [t.to_dict() for t in tables]
        }

    @router.post("/execute-sql")
    async def execute_sql(
        request: Request,
        x_pnp_timestamp: Optional[str] = Header(None),
        x_pnp_signature: Optional[str] = Header(None)
    ):
        body = await _authenticate_request(request, x_pnp_timestamp or "0", x_pnp_signature or "")
        payload = json.loads(body.decode("utf-8"))
        sql = payload.get("sql")
        params = payload.get("params", {})
        max_rows = payload.get("max_rows", 50)

        if not sql:
            raise HTTPException(status_code=400, detail="Missing SQL query in request payload.")

        try:
            rows = executor.execute_query(sql, params, max_rows)
            return {"rows": rows, "count": len(rows)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database execution error: {e}")

    return router
