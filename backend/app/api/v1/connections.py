from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from app.core.database import get_db
from app.models.connections import Connection, SemanticTable, SemanticColumn
from app.models.tenants import Tenant
from app.schemas.connections import ConnectionCreate, ConnectionResponse, SemanticTableCreate
from app.services.connectors.dispatcher import ConnectorDispatcher

router = APIRouter(prefix="/connections", tags=["Client Connections & Schema"])


from app.core.crypto import CryptoService
from pydantic import BaseModel
from app.services.connectors.direct_db import DirectDBExecutor


from app.services.connectors.schema_parser import SchemaDDLParser


class TestDBRequest(BaseModel):
    database_url: str


class ParseSchemaRequest(BaseModel):
    schema_text: str


import logging

logger = logging.getLogger(__name__)


@router.post("/test-db", status_code=status.HTTP_200_OK)
async def test_db_connection(payload: TestDBRequest):
    """
    Connects directly to a client's database using their connection URL.
    Returns the list of available tables. No middleware or connector needed.
    """
    db_url = payload.database_url.strip()
    if not db_url:
        return {"status": "error", "message": "Database URL is required.", "tables": []}

    try:
        result = await DirectDBExecutor.test_connection(db_url)
        return result
    except Exception as e:
        logger.error(f"Unexpected error testing DB connection: {e}")
        return {"status": "error", "message": f"Connection error: {str(e)}", "tables": []}


@router.post("/parse-schema", status_code=status.HTTP_200_OK)
async def parse_schema_ddl(payload: ParseSchemaRequest):
    """
    Zero-Knowledge Schema Parser: Parses raw SQL DDL, Prisma Schema, or JSON definitions
    into structured table & column schemas without connecting to any external database.
    """
    raw_text = payload.schema_text.strip()
    if not raw_text:
        return {"status": "error", "message": "Schema definition is required.", "tables": [], "table_names": []}

    tables = SchemaDDLParser.parse(raw_text)
    table_names = [t["table_name"] for t in tables]
    return {
        "status": "success",
        "tables": tables,
        "table_names": table_names,
        "total_tables": len(tables)
    }



@router.post("/{tenant_id}", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(tenant_id: str, payload: ConnectionCreate, db: AsyncSession = Depends(get_db)):
    """Register a new client connector bridge for a tenant."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Tenant not found.")

    conn = Connection(
        tenant_id=tenant_id,
        name=payload.name,
        connection_type=payload.connection_type,
        endpoint_url=payload.endpoint_url,
        auth_secret_hash=CryptoService.encrypt(payload.shared_secret)
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return conn


@router.post("/{connection_id}/sync-schema", status_code=status.HTTP_200_OK)
async def sync_schema_from_connector(connection_id: str, db: AsyncSession = Depends(get_db)):
    """
    Connects to the client's connector endpoint, fetches the sanitized schema dictionary,
    and populates or updates SemanticTable and SemanticColumn records.
    """
    stmt = select(Connection).where(Connection.id == connection_id).options(
        selectinload(Connection.tables).selectinload(SemanticTable.columns)
    )
    result = await db.execute(stmt)
    conn = result.scalars().first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found.")

    dispatcher = ConnectorDispatcher(
        endpoint_url=conn.endpoint_url,
        shared_secret=CryptoService.decrypt(conn.auth_secret_hash) if conn.auth_secret_hash else "default_secret"
    )

    try:
        schema_data = await dispatcher.fetch_schema()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to communicate with client connector: {e}")

    # Process tables from connector
    tables_list = schema_data.get("tables", [])
    synced_tables = []

    for tbl_data in tables_list:
        table_name = tbl_data.get("table_name")
        stmt_t = select(SemanticTable).where(
            SemanticTable.connection_id == conn.id,
            SemanticTable.table_name == table_name
        )
        res_t = await db.execute(stmt_t)
        existing_table = res_t.scalars().first()

        if not existing_table:
            existing_table = SemanticTable(
                tenant_id=conn.tenant_id,
                connection_id=conn.id,
                table_name=table_name,
                business_name=tbl_data.get("business_name", table_name),
                description=tbl_data.get("description", ""),
                allowed_roles=tbl_data.get("allowed_roles", ["admin", "user", "student", "faculty"])
            )
            db.add(existing_table)
            await db.flush()

        # Process columns
        cols_data = tbl_data.get("columns", [])
        for col_info in cols_data:
            col_name = col_info.get("column_name")
            stmt_c = select(SemanticColumn).where(
                SemanticColumn.table_id == existing_table.id,
                SemanticColumn.column_name == col_name
            )
            res_c = await db.execute(stmt_c)
            existing_col = res_c.scalars().first()

            if not existing_col:
                new_col = SemanticColumn(
                    table_id=existing_table.id,
                    column_name=col_name,
                    data_type=col_info.get("data_type", "TEXT"),
                    business_meaning=col_info.get("business_meaning", col_name),
                    allowed_operations=col_info.get("allowed_operations", ["SELECT", "WHERE", "JOIN"]),
                    is_sensitive=col_info.get("is_sensitive", False),
                    row_identity_binding=col_info.get("row_identity_binding", None)
                )
                db.add(new_col)

        synced_tables.append(table_name)

    await db.commit()
    return {"status": "success", "synced_tables": synced_tables}

