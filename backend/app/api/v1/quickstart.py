import uuid
import re
import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.database import get_db
from app.models.tenants import Tenant
from app.models.agents import Agent
from app.models.connections import Connection, SemanticTable, SemanticColumn
from app.models.rag import RAGSource, RAGChunk
from app.services.rag.chunker import TextChunker
from app.services.rag.embedder import EmbeddingService
from app.core.crypto import CryptoService
from app.services.connectors.direct_db import DirectDBExecutor
from app.services.guardrails.compiler import AIGuardrailCompiler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quickstart", tags=["Quickstart Onboarding Wizard"])


from app.services.connectors.schema_parser import SchemaDDLParser

class QuickstartSetupRequest(BaseModel):
    tenant_id: Optional[str] = Field(default=None, description="Optional tenant_id from active session")
    project_name: str = Field(..., description="Name of the client website or project, e.g. 'Attendance System'")
    agent_name: str = Field(default="AI Assistant", description="Name of the agent, e.g. 'Support Bot'")
    service_type: str = Field(default="hybrid", description="Service mode: 'rag', 'sql', or 'hybrid'")
    document_title: Optional[str] = Field(default=None, description="Title of document/policy")
    document_content: Optional[str] = Field(default=None, description="Text content of policy, FAQ, or documentation")
    connection_mode: Optional[str] = Field(default="direct", description="Connection mode: 'direct' or 'schema_only'")
    databases: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of multiple database connections, each with name, engine, database_url, selected_tables")
    database_url: Optional[str] = Field(default=None, description="Read-only database connection URL, e.g. postgresql://readonly:pass@host:5432/db")
    schema_ddl: Optional[str] = Field(default=None, description="Raw SQL DDL, Prisma, or JSON schema for Zero-Knowledge mode")
    selected_tables: Optional[List[str]] = Field(default=None, description="List of table names the AI is allowed to query")
    guardrail_guidelines: Optional[str] = Field(default=None, description="Plain English restrictions from client")
    guardrail_config: Optional[Dict[str, Any]] = Field(default=None, description="Pre-compiled guardrail JSON configuration")
    target_audience: Optional[str] = Field(default="end_user", description="Target audience: 'end_user', 'staff', 'management', 'adaptive'")
    escalation_webhook_url: Optional[str] = Field(default=None, description="Optional Slack/Discord/CRM webhook URL for live human escalation alerts")
    escalation_email: Optional[str] = Field(default=None, description="Optional Support Email for instant notification alerts")
    support_contact_phone: Optional[str] = Field(default=None, description="Optional direct support phone for widget contact card")
    support_contact_email: Optional[str] = Field(default=None, description="Optional direct support email for widget contact card")


@router.post("/setup", status_code=status.HTTP_201_CREATED)
async def setup_custom_agent(payload: QuickstartSetupRequest, db: AsyncSession = Depends(get_db)):
    """
    All-in-one visual onboarding endpoint:
    1. Attaches to existing Tenant or provisions new Tenant
    2. Provisions AI Agent tailored to service_type ('rag', 'sql', 'hybrid') and target_audience
    3. If RAG/Hybrid: Chunks, embeds, and stores documents into Neon PostgreSQL with FastEmbed
    4. If SQL/Hybrid: Connects directly to client's database and discovers schema
    5. Compiles and attaches AI Guardrail policy
    6. Returns personalized embed code and starter test questions for the in-platform sandbox
    """
    tenant = None
    if payload.tenant_id:
        stmt_t = select(Tenant).where(Tenant.id == payload.tenant_id)
        res_t = await db.execute(stmt_t)
        tenant = res_t.scalars().first()

    if not tenant:
        slug = re.sub(r"[^a-z0-9]+", "-", payload.project_name.lower()).strip("-")
        if not slug:
            slug = f"project-{uuid.uuid4().hex[:6]}"

        stmt_s = select(Tenant).where(Tenant.slug == slug)
        res_s = await db.execute(stmt_s)
        tenant = res_s.scalars().first()

        if not tenant:
            tenant = Tenant(
                name=payload.project_name,
                slug=slug
            )
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)

    # Compile Guardrails if guidelines provided, or use target audience preset
    final_guardrail_config = payload.guardrail_config
    if not final_guardrail_config and payload.guardrail_guidelines and payload.guardrail_guidelines.strip():
        final_guardrail_config = await AIGuardrailCompiler.compile_guidelines(
            guidelines=payload.guardrail_guidelines.strip(),
            table_schemas=payload.selected_tables or [],
            doc_titles=[payload.document_title] if payload.document_title else []
        )
    elif not final_guardrail_config:
        # Auto-apply audience preset defaults
        aud_preset = AIGuardrailCompiler.get_audience_preset(payload.target_audience or "end_user")
        final_guardrail_config = {
            "target_audience": payload.target_audience or "end_user",
            "banned_intents": aud_preset.get("banned_intents", []),
            "restricted_columns": aud_preset.get("restricted_columns", []),
            "row_level_security": aud_preset.get("row_level_security", {}),
            "refusal_instructions": [aud_preset.get("suggested_rules", "Follow enterprise boundaries strictly.")],
            "refusal_message": "I cannot fulfill this request due to enterprise access restrictions."
        }

    # Attach escalation settings if provided
    if not isinstance(final_guardrail_config, dict):
        final_guardrail_config = {}

    if payload.escalation_webhook_url and payload.escalation_webhook_url.strip():
        final_guardrail_config["escalation_webhook_url"] = payload.escalation_webhook_url.strip()
    if payload.escalation_email and payload.escalation_email.strip():
        final_guardrail_config["escalation_email"] = payload.escalation_email.strip()
    if payload.support_contact_phone and payload.support_contact_phone.strip():
        final_guardrail_config["support_contact_phone"] = payload.support_contact_phone.strip()
    if payload.support_contact_email and payload.support_contact_email.strip():
        final_guardrail_config["support_contact_email"] = payload.support_contact_email.strip()

    # 2. Create Agent
    agent = Agent(
        tenant_id=tenant.id,
        name=payload.agent_name,
        description=f"{payload.service_type.upper()} Assistant for {payload.project_name}",
        model_provider="groq",
        model_name="qwen/qwen3.8-27b",
        guardrail_config=json.dumps(final_guardrail_config) if final_guardrail_config else None
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    chunks_indexed = 0
    test_questions = []

    # 3. Process & Ingest Documents (RAG) - Only if service_type in ('rag', 'hybrid')
    if payload.service_type in {"rag", "hybrid"}:
        if payload.document_content and payload.document_content.strip():
            doc_title = payload.document_title or f"{payload.project_name} Guidelines"
            source = RAGSource(
                tenant_id=tenant.id,
                agent_id=agent.id,
                name=doc_title,
                source_type="text_paste"
            )
            db.add(source)
            await db.commit()
            await db.refresh(source)

            chunks = TextChunker.chunk_text(payload.document_content, chunk_size=350, chunk_overlap=40)
            for c in chunks:
                emb = await EmbeddingService.get_embedding(c)
                rag_chunk = RAGChunk(
                    tenant_id=tenant.id,
                    rag_source_id=source.id,
                    content=c,
                    doc_metadata={
                        "title": doc_title,
                        "allowed_roles": ["student", "faculty", "admin", "user", "customer"]
                    },
                    embedding=emb
                )
                db.add(rag_chunk)
                chunks_indexed += 1

            await db.commit()
            test_questions.append(f"What is the official policy regarding {doc_title}?")

    tables_synced = 0
    # 4. Database Connection (SQL) - Only if service_type in ('sql', 'hybrid')
    if payload.service_type in {"sql", "hybrid"}:
        if payload.connection_mode == "schema_only" or (payload.schema_ddl and payload.schema_ddl.strip()):
            # --- Zero-Knowledge Schema-Only Mode ---
            raw_ddl = (payload.schema_ddl or "").strip()
            if raw_ddl:
                # Deactivate previous connections
                stmt_deact = (
                    update(Connection)
                    .where(Connection.tenant_id == tenant.id)
                    .values(is_active=False)
                )
                await db.execute(stmt_deact)

                conn = Connection(
                    tenant_id=tenant.id,
                    name=f"{payload.project_name} Zero-Knowledge Schema",
                    connection_type="schema_only",
                    endpoint_url=None,
                    auth_secret_hash=None,
                    is_active=True
                )
                db.add(conn)
                await db.commit()
                await db.refresh(conn)

                parsed_tables = SchemaDDLParser.parse(raw_ddl)
                for t_dict in parsed_tables:
                    sem_table = SemanticTable(
                        connection_id=conn.id,
                        tenant_id=tenant.id,
                        table_name=t_dict["table_name"],
                        business_name=t_dict.get("business_name", t_dict["table_name"]),
                        description=t_dict.get("description", ""),
                        allowed_roles=["user", "admin", "student", "faculty", "customer"]
                    )
                    db.add(sem_table)
                    await db.flush()

                    for c_dict in t_dict.get("columns", []):
                        sem_col = SemanticColumn(
                            table_id=sem_table.id,
                            column_name=c_dict["column_name"],
                            data_type=c_dict.get("data_type", "TEXT"),
                            business_meaning=c_dict.get("business_meaning", c_dict["column_name"]),
                            allowed_operations=["SELECT", "WHERE", "JOIN"],
                            is_sensitive=c_dict.get("is_sensitive", False),
                            row_identity_binding=None
                        )
                        db.add(sem_col)
                    tables_synced += 1
                await db.commit()
                if parsed_tables:
                    test_questions.append(f"Show me summary from {parsed_tables[0]['table_name']}")

        elif payload.databases or (payload.database_url and payload.database_url.strip()):
            # --- Direct Cloud DB Connection Mode (Multi-DB Federation Support) ---
            db_list = payload.databases or []
            if not db_list and payload.database_url and payload.database_url.strip():
                db_list = [{
                    "name": f"{payload.project_name} Database",
                    "database_url": payload.database_url.strip(),
                    "selected_tables": payload.selected_tables or []
                }]

            # Deactivate previous connections for this tenant for a clean setup
            stmt_deact = (
                update(Connection)
                .where(Connection.tenant_id == tenant.id)
                .values(is_active=False)
            )
            await db.execute(stmt_deact)

            for idx, db_item in enumerate(db_list):
                db_url = (db_item.get("database_url") or "").strip()
                if not db_url:
                    continue
                db_name = db_item.get("name") or f"{payload.project_name} DB #{idx+1}"
                selected_tables = db_item.get("selected_tables") or []

                # Store encrypted connection
                conn = Connection(
                    tenant_id=tenant.id,
                    name=db_name,
                    connection_type="direct_db",
                    endpoint_url=CryptoService.encrypt(db_url),
                    auth_secret_hash=None,
                    is_active=True
                )
                db.add(conn)
                await db.commit()
                await db.refresh(conn)

                # Discover schema from client's database directly
                try:
                    if not selected_tables:
                        test_result = await DirectDBExecutor.test_connection(db_url)
                        selected_tables = test_result.get("tables", [])

                    schema_data = await DirectDBExecutor.discover_schema(db_url, selected_tables)
                    for t_dict in schema_data:
                        sem_table = SemanticTable(
                            connection_id=conn.id,
                            tenant_id=tenant.id,
                            table_name=t_dict["table_name"],
                            business_name=t_dict.get("business_name", t_dict["table_name"]),
                            description=t_dict.get("description", f"Table from {db_name}"),
                            allowed_roles=["user", "admin", "student", "faculty", "customer"]
                        )
                        db.add(sem_table)
                        await db.flush()

                        for c_dict in t_dict.get("columns", []):
                            sem_col = SemanticColumn(
                                table_id=sem_table.id,
                                column_name=c_dict["column_name"],
                                data_type=c_dict.get("data_type", "TEXT"),
                                business_meaning=c_dict.get("business_meaning", c_dict["column_name"]),
                                allowed_operations=["SELECT", "WHERE", "JOIN"],
                                is_sensitive=c_dict.get("is_sensitive", False),
                                row_identity_binding=None
                            )
                            db.add(sem_col)
                        tables_synced += 1
                    await db.commit()
                    if selected_tables:
                        test_questions.append(f"Show me data from {selected_tables[0]} in {db_name}")
                except Exception as e:
                    logger.warning(f"Schema discovery failed for {db_name}: {e}")
                    # Fallback: create SemanticTable records directly from selected_tables
                    if selected_tables:
                        for tbl in selected_tables:
                            sem_table = SemanticTable(
                                connection_id=conn.id,
                                tenant_id=tenant.id,
                                table_name=tbl,
                                business_name=tbl.replace("_", " ").title(),
                                description=f"Table from {db_name}",
                                allowed_roles=["user", "admin", "student", "faculty", "customer"]
                            )
                            db.add(sem_table)
                            await db.flush()
                            # Default standard columns
                            for col in ["id", "created_at", "status", "name", "value"]:
                                db.add(SemanticColumn(
                                    table_id=sem_table.id,
                                    column_name=col,
                                    data_type="TEXT",
                                    business_meaning=col.replace("_", " ").title(),
                                    allowed_operations=["SELECT", "WHERE", "JOIN"],
                                    is_sensitive=False
                                ))
                        await db.commit()
                        test_questions.append(f"Show me data from {selected_tables[0]} in {db_name}")

    if not test_questions:
        test_questions = ["Hello, what can you help me with?"]

    # Generate Embed Snippet
    embed_snippet = (
        f'<script\n'
        f'  src="http://127.0.0.1:8000/static/pnp-widget.js"\n'
        f'  data-api-host="http://127.0.0.1:8000"\n'
        f'  data-agent-id="{agent.id}"\n'
        f'  data-title="{payload.agent_name}"\n'
        f'  data-subtitle="{payload.project_name}">\n'
        f'</script>'
    )

    return {
        "status": "success",
        "service_type": payload.service_type,
        "tenant_id": tenant.id,
        "tenant_slug": tenant.slug,
        "agent_id": agent.id,
        "agent_name": agent.name,
        "chunks_indexed": chunks_indexed,
        "tables_synced": tables_synced,
        "guardrail_config": final_guardrail_config,
        "embed_snippet": embed_snippet,
        "test_questions": test_questions
    }
