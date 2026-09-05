import time
import json
import asyncio
import logging
import re
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.tenants import Tenant
from app.models.agents import Agent
from app.models.connections import Connection, SemanticTable, SemanticColumn
from app.models.chat import ChatSession, ChatMessage, QueryLog
from app.services.router.intent_router import IntentRouter
from app.services.router.contextualizer import QueryContextualizer
from app.services.sql.generator import TextToSQLEngine
from app.services.sql.mongo_generator import TextToMQLEngine
from app.services.sql.validator import SQLASTValidator, SQLSecurityViolation
from app.services.connectors.direct_db import detect_db_type
from app.services.rag.retriever import RAGRetriever
from app.services.llm.gateway import LLMGateway
from app.services.cache.redis_cache import RedisService
from app.core.crypto import CryptoService
from app.services.connectors.dispatcher import ConnectorDispatcher
from app.services.connectors.direct_db import DirectDBExecutor
from app.services.guardrails.compiler import AIGuardrailCompiler
from app.models.actions import ActionDefinition
from app.services.actions.tool_compiler import ActionToolCompiler
from app.services.actions.dispatcher import ActionDispatcher

logger = logging.getLogger(__name__)

# =========================================================================
# ZERO-HEDGING CLEANER & REGEX SAFETY NET
# =========================================================================
HEDGING_PATTERNS = [
    re.compile(r"^(according to (the )?(provided |uploaded |given |available )?(documents?|resources?|context|database records?|database|records?|information|system|policies?|handbook|knowledge base)(\s*(provided|available|given))?),?\s*", re.IGNORECASE),
    re.compile(r"^(based on (the )?(provided |uploaded |given |available )?(documents?|resources?|context|database records?|database|records?|information|system|policies?|handbook|knowledge base)(\s*(provided|available|given))?),?\s*", re.IGNORECASE),
    re.compile(r"^(as per (the )?(provided |uploaded |given |available )?(documents?|resources?|context|database records?|database|records?|policies?|guidelines?)(\s*(provided|available|given))?),?\s*", re.IGNORECASE),
    re.compile(r"^(from the (provided |uploaded |given |available )?(documents?|resources?|context|database records?|database|records?|policies?|guidelines?)(\s*(provided|available|given))?),?\s*", re.IGNORECASE),
    re.compile(r"^(the provided (documents?|context|database records?|resources?) (states?|indicates?|shows?|specif(y|ies)) that),?\s*", re.IGNORECASE),
    re.compile(r"^(in the (provided |uploaded |available )?(documents?|resources?|context|database records?|database)),?\s*", re.IGNORECASE),
]

def clean_hedging_prefix(text: str, preserve_trailing_space: bool = False) -> str:
    """Removes robotic hedging preamble while preserving natural capitalized grammar."""
    if not text:
        return text
    had_trailing_space = text.endswith(" ")
    cleaned = text.strip()
    changed = True
    while changed:
        changed = False
        for pat in HEDGING_PATTERNS:
            new_text = pat.sub("", cleaned)
            if new_text != cleaned:
                cleaned = new_text.strip()
                changed = True
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    if preserve_trailing_space and had_trailing_space and not cleaned.endswith(" "):
        cleaned += " "
    return cleaned


class QueryOrchestrator:
    """
    Central AI Execution Engine:
    Routes query, coordinates SQL / RAG / Hybrid engines, enforces AI Guardrails,
    logs performance metrics, and produces verified streaming or non-streaming responses.
    """

    @classmethod
    async def process_query(
        cls,
        db: AsyncSession,
        session: ChatSession,
        user_query: str
    ) -> Dict[str, Any]:
        """
        Executes query end-to-end and records telemetry in QueryLog.
        """
        start_time = time.time()
        tenant_id = session.tenant_id
        user_role = session.user_role or "user"
        external_user_id = session.external_user_id

        # 💳 Quota & Billing Check
        tenant = await db.get(Tenant, tenant_id)
        if tenant:
            limit = tenant.monthly_query_limit or 150
            used = tenant.queries_used_this_month or 0
            if used >= limit:
                refusal_msg = f"This AI Assistant has reached its monthly allowance of {limit} queries. Please upgrade your plan in the Plug-N-Play AI dashboard to resume responses."
                return {
                    "answer": refusal_msg,
                    "route_chosen": "QUOTA_EXCEEDED",
                    "structured_data": None,
                    "rag_sources": [],
                    "generated_sql": None,
                    "session_id": session.id,
                    "cached": False,
                    "quota_exceeded": True
                }
            tenant.queries_used_this_month = used + 1

        # Fetch Agent & Guardrail Configuration
        agent = None
        guardrail_config = None
        if session.agent_id:
            agent = await db.get(Agent, session.agent_id)
            if agent and agent.guardrail_config:
                try:
                    guardrail_config = json.loads(agent.guardrail_config)
                except Exception:
                    pass

        # 0. Contextualize follow-up query using conversation history
        effective_query = await QueryContextualizer.contextualize_query(db, session.id, user_query)

        # 🛡️ GATE 1: Fast Intent Guardrail Evaluation (0 LLM tokens, sub-1ms)
        is_blocked, refusal_msg = AIGuardrailCompiler.evaluate_query(effective_query, guardrail_config, user_role=user_role)
        if not is_blocked and effective_query != user_query:
            is_blocked, refusal_msg = AIGuardrailCompiler.evaluate_query(user_query, guardrail_config, user_role=user_role)

        if is_blocked:
            logger.info(f"Session {session.id} BLOCKED by guardrail: '{user_query}'")
            query_log = QueryLog(
                tenant_id=tenant_id,
                session_id=session.id,
                user_query=user_query,
                route_chosen="GUARDRAIL_BLOCKED",
                generated_sql=None,
                sql_execution_ms=0,
                rag_retrieval_ms=0,
                llm_generation_ms=1,
                total_tokens=len(user_query.split()) + len(refusal_msg.split()),
                error_message=None
            )
            db.add(query_log)
            await db.commit()

            return {
                "answer": refusal_msg,
                "route_chosen": "GUARDRAIL_BLOCKED",
                "structured_data": None,
                "rag_sources": [],
                "generated_sql": None,
                "session_id": session.id,
                "cached": False,
                "guardrail_blocked": True
            }

        # 0. Check Redis exact query cache (sub-5ms response)
        cached_result = await RedisService.get_query_cache(
            agent_id=session.agent_id,
            user_role=user_role,
            user_id=external_user_id,
            query=effective_query
        )
        if cached_result:
            logger.info(f"Session {session.id} served from Redis query cache!")
            return cached_result

        # ⚡ ACTION & TOOL LAYER: Check for executable action intent
        if session.agent_id:
            act_stmt = select(ActionDefinition).where(
                ActionDefinition.agent_id == session.agent_id,
                ActionDefinition.is_active == True
            )
            act_res = await db.execute(act_stmt)
            active_actions = act_res.scalars().all()
            if active_actions:
                detected = await ActionToolCompiler.detect_action_intent(
                    query=effective_query,
                    actions=active_actions,
                    user_role=user_role
                )
                if detected:
                    action, extracted_params = detected
                    agent_name = agent.name if agent else "Plug-N-Play AI"
                    if action.requires_user_confirmation:
                        proposal = {
                            "action_id": action.id,
                            "name": action.name,
                            "display_name": action.display_name,
                            "parameters": extracted_params,
                            "requires_confirmation": True,
                            "execution_target": getattr(action, "execution_target", "server") or "server",
                            "endpoint_url": action.endpoint_url,
                            "http_method": (action.http_method or "POST").upper(),
                            "client_event_name": getattr(action, "client_event_name", None)
                        }
                        ans = f"I have prepared your request to **{action.display_name}**. Please review the details below and confirm to execute."
                        query_log = QueryLog(
                            tenant_id=tenant_id,
                            session_id=session.id,
                            user_query=user_query,
                            route_chosen="ACTION_PROPOSAL",
                            total_tokens=len(user_query.split()) + len(ans.split())
                        )
                        db.add(query_log)
                        await db.commit()
                        return {
                            "answer": ans,
                            "route_chosen": "ACTION_PROPOSAL",
                            "action_proposal": proposal,
                            "structured_data": None,
                            "rag_sources": [],
                            "generated_sql": None,
                            "session_id": session.id,
                            "cached": False
                        }
                    else:
                        exec_res = await ActionDispatcher.dispatch_action(
                            action=action,
                            parameters=extracted_params,
                            tenant_id=tenant_id,
                            external_user_id=external_user_id,
                            session_id=session.id,
                            db=db,
                            agent_name=agent_name
                        )
                        query_log = QueryLog(
                            tenant_id=tenant_id,
                            session_id=session.id,
                            user_query=user_query,
                            route_chosen="ACTION_EXECUTED",
                            total_tokens=len(user_query.split()) + len(exec_res.natural_confirmation.split())
                        )
                        db.add(query_log)
                        await db.commit()
                        return {
                            "answer": exec_res.natural_confirmation,
                            "route_chosen": "ACTION_EXECUTED",
                            "action_proposal": None,
                            "structured_data": exec_res.response_data,
                            "rag_sources": [],
                            "generated_sql": None,
                            "session_id": session.id,
                            "cached": False
                        }

        # 1. Route Intent with Agent Service Type Awareness
        if agent and agent.description and agent.description.upper().startswith("RAG"):
            intent, reason = "RAG", "Agent configured strictly for Document RAG"
        elif agent and agent.description and agent.description.upper().startswith("SQL"):
            intent, reason = "SQL", "Agent configured strictly for Text-to-SQL"
        else:
            intent, reason = await IntentRouter.route_query(effective_query)
        logger.info(f"Session {session.id} routed as {intent} (Reason: {reason})")

        sql_rows: Optional[List[Dict[str, Any]]] = None
        rag_chunks: Optional[List[Dict[str, Any]]] = None
        generated_sql: Optional[str] = None
        error_msg: Optional[str] = None
        
        sql_time_ms = 0
        rag_time_ms = 0
        llm_time_ms = 0

        try:
            # 2. Execute Engines based on Intent
            if intent in {"SQL", "HYBRID"}:
                t0 = time.time()
                try:
                    sql_rows, generated_sql = await cls._execute_sql_pipeline(
                        db, tenant_id, effective_query, external_user_id, user_role, guardrail_config=guardrail_config
                    )
                    sql_time_ms = int((time.time() - t0) * 1000)
                except Exception as e:
                    logger.info(f"SQL execution bypassed or no queryable tables ({e}), checking RAG knowledge base")
                    sql_rows = None

            # Always check RAG if intent is RAG/HYBRID or if SQL returned no records
            if intent in {"RAG", "HYBRID"} or not sql_rows:
                t0 = time.time()
                try:
                    rag_chunks = await RAGRetriever.retrieve_relevant_chunks(
                        db, tenant_id, effective_query, user_role=user_role, top_k=4
                    )
                    rag_time_ms = int((time.time() - t0) * 1000)
                    if rag_chunks and not sql_rows and intent == "SQL":
                        intent = "RAG"
                except Exception as e:
                    logger.error(f"RAG retrieval error: {e}")

            # 3. Synthesize Final Answer with LLM
            # Wait for Groq TPM window to partially reset between calls
            if intent in {"SQL", "HYBRID"} and sql_rows is not None:
                await asyncio.sleep(2.0)
            t0 = time.time()
            agent_name = agent.name if agent else "Plug-N-Play AI"
            workspace_name = tenant.name if (tenant and tenant.name) else "Plug-N-Play AI"
            answer = await cls._synthesize_response(
                user_query=effective_query,
                intent=intent,
                sql_rows=sql_rows,
                rag_chunks=rag_chunks,
                user_role=user_role,
                user_id=external_user_id,
                guardrail_config=guardrail_config,
                agent_name=agent_name,
                workspace_name=workspace_name
            )
            llm_time_ms = int((time.time() - t0) * 1000)

        except Exception as e:
            logger.error(f"Error during query orchestration: {e}", exc_info=True)
            error_msg = str(e)
            answer = f"I encountered an issue processing your request: {error_msg}"

        # 4. Save Query Log & Telemetry
        query_log = QueryLog(
            tenant_id=tenant_id,
            session_id=session.id,
            user_query=user_query,
            route_chosen=intent,
            generated_sql=generated_sql,
            sql_execution_ms=sql_time_ms,
            rag_retrieval_ms=rag_time_ms,
            llm_generation_ms=llm_time_ms,
            total_tokens=len(user_query.split()) + len(answer.split()),
            error_message=error_msg
        )
        db.add(query_log)
        await db.commit()

        result_payload = {
            "answer": answer,
            "route_chosen": intent,
            "structured_data": sql_rows,
            "rag_sources": rag_chunks,
            "generated_sql": generated_sql,
            "session_id": session.id,
            "cached": False
        }

        # Cache in Redis if successful
        if not error_msg and answer:
            await RedisService.set_query_cache(
                agent_id=session.agent_id,
                user_role=user_role,
                user_id=external_user_id,
                query=user_query,
                response_data=result_payload,
                ttl=300
            )

        return result_payload

    @classmethod
    async def _execute_sql_pipeline(
        cls,
        db: AsyncSession,
        tenant_id: str,
        user_query: str,
        user_id: Optional[str],
        user_role: str,
        guardrail_config: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], str]:
        """Runs schema assembly, Text-to-SQL prompt, AST safety validation, and connector execution."""
        # 1. Fetch active connection
        stmt_conn = (
            select(Connection)
            .where(Connection.tenant_id == tenant_id, Connection.is_active == True)
            .order_by(Connection.created_at.desc())
        )
        res_conn = await db.execute(stmt_conn)
        conn = res_conn.scalars().first()
        if not conn:
            raise RuntimeError("No active client database connection configured for this tenant.")

        # 2. Fetch active tables/collections scoped to this specific connection
        stmt_tables = (
            select(SemanticTable)
            .where(
                SemanticTable.tenant_id == tenant_id, 
                SemanticTable.connection_id == conn.id,
                SemanticTable.is_queryable == True
            )
            .options(selectinload(SemanticTable.columns))
        )
        res_tables = await db.execute(stmt_tables)
        tables = res_tables.scalars().all()
        
        # Fallback to tenant-level tables if connection_id was not set (legacy records)
        if not tables:
            stmt_tables_fb = (
                select(SemanticTable)
                .where(SemanticTable.tenant_id == tenant_id, SemanticTable.is_queryable == True)
                .options(selectinload(SemanticTable.columns))
            )
            res_tables_fb = await db.execute(stmt_tables_fb)
            tables = res_tables_fb.scalars().all()

        if not tables:
            raise RuntimeError(f"No queryable tables/collections configured for connection '{conn.name}'.")

        allowed_tables = {
            t.table_name for t in tables 
            if not t.allowed_roles or user_role in t.allowed_roles or "admin" in t.allowed_roles
        }

        # Define elevated roles that have authority to view departmental / cross-student records
        ELEVATED_MANAGEMENT_ROLES = {
            "admin", "tpo", "placement_officer", "faculty", "staff", 
            "management", "manager", "superadmin", "recruiter", "director", "dean"
        }
        role_is_elevated = bool(user_role and user_role.lower() in ELEVATED_MANAGEMENT_ROLES)
        is_self_query = bool(re.search(r"\b(my|mine|me|myself|i am|for me)\b", user_query.lower()))

        # 🛡️ GATE 2: Extract Restricted Columns from Guardrail Policy
        restricted_cols = set()
        if guardrail_config and guardrail_config.get("restricted_columns"):
            raw_restricted = {c.lower().strip() for c in guardrail_config["restricted_columns"]}
            ACADEMIC_FIELDS = {"cgpa", "gpa", "sgpa", "marks", "attendance", "grade", "grades", "score", "scores", "rank", "percentage"}
            if role_is_elevated or is_self_query:
                # Do not strip academic / performance columns for TPO or student's own inquiry
                restricted_cols = {c for c in raw_restricted if c not in ACADEMIC_FIELDS}
            else:
                restricted_cols = raw_restricted

        # Decrypt the database URL for direct connections
        db_url = None
        is_mongodb = False
        if conn.connection_type == "direct_db":
            db_url = CryptoService.decrypt(conn.endpoint_url)
            try:
                is_mongodb = detect_db_type(db_url) == "mongodb"
            except ValueError:
                pass

        # ── MongoDB Path ──
        if is_mongodb:
            schema_context = TextToMQLEngine.build_schema_context(
                tables, user_role=user_role, user_query=user_query, restricted_columns=restricted_cols
            )
            prompt = TextToMQLEngine.create_mql_prompt(
                user_query, schema_context, user_id=user_id, user_role=user_role
            )
            llm_response = await LLMGateway.complete([
                {"role": "user", "content": prompt}
            ], temperature=0.0, max_tokens=220)

            collection_name, pipeline = TextToMQLEngine.extract_and_validate(
                raw_llm_response=llm_response,
                allowed_collections=allowed_tables
            )
            rows = await DirectDBExecutor.execute_mongo_query(db_url, collection_name, pipeline)
            
            # 🛡️ Post-Execution Data Scrubber (MongoDB)
            if restricted_cols and rows:
                rows = [
                    {k: v for k, v in r.items() if k.lower().strip() not in restricted_cols}
                    if isinstance(r, dict) else r
                    for r in rows
                ]
            return rows, f"db.{collection_name}.aggregate({json.dumps(pipeline, default=str)})"

        # ── SQL Path (PostgreSQL / MySQL / SQLite) ──
        schema_context = TextToSQLEngine.build_schema_context(
            tables, user_role=user_role, user_query=user_query, restricted_columns=restricted_cols
        )

        allowed_columns = {
            t.table_name: {
                c.column_name for c in t.columns 
                if not c.is_sensitive and c.column_name.lower() not in restricted_cols
            }
            for t in tables
            if t.table_name in allowed_tables
        }

        # Check for row identity binding / Row-Level Security
        identity_filter = None
        for t in tables:
            if t.table_name in allowed_tables:
                for c in t.columns:
                    if c.row_identity_binding == "auth_user_id" and user_id and not role_is_elevated:
                        identity_filter = (t.table_name, c.column_name, user_id)
                        break

        dialect = "sqlite" if ("sqlite" in conn.connection_type.lower() or "sqlite" in (conn.endpoint_url or "").lower() or "testserver" in (conn.endpoint_url or "")) else "postgres"

        prompt = TextToSQLEngine.create_sql_prompt(
            user_query, schema_context, user_id=user_id, user_role=user_role, dialect=dialect
        )
        llm_response = await LLMGateway.complete([
            {"role": "user", "content": prompt}
        ], temperature=0.0, max_tokens=120)

        sanitized_sql, bound_params = TextToSQLEngine.extract_and_validate(
            raw_llm_response=llm_response,
            allowed_tables=allowed_tables,
            allowed_columns=allowed_columns,
            identity_filter=identity_filter,
            dialect=dialect
        )

        # Execute query with Automated Self-Healing Reflection Loop
        rows = None
        try:
            if conn.connection_type == "direct_db":
                rows = await DirectDBExecutor.execute_readonly(db_url, sanitized_sql, bound_params)
            else:
                dispatcher = ConnectorDispatcher(
                    endpoint_url=conn.endpoint_url,
                    shared_secret=CryptoService.decrypt(conn.auth_secret_hash) if conn.auth_secret_hash else "default_secret"
                )
                rows = await dispatcher.execute_sql(sanitized_sql, bound_params)
        except Exception as exec_err:
            logger.warning(f"SQL execution error: {exec_err}. Triggering Reflection Self-Healing loop...")
            try:
                repair_prompt = TextToSQLEngine.create_sql_repair_prompt(
                    user_query=user_query,
                    failed_sql=sanitized_sql,
                    error_message=str(exec_err),
                    schema_context=schema_context,
                    dialect=dialect
                )
                repair_response = await LLMGateway.complete([
                    {"role": "user", "content": repair_prompt}
                ], temperature=0.0, max_tokens=150)
                healed_sql, healed_params = TextToSQLEngine.extract_and_validate(
                    raw_llm_response=repair_response,
                    allowed_tables=allowed_tables,
                    allowed_columns=allowed_columns,
                    identity_filter=identity_filter,
                    dialect=dialect
                )
                if conn.connection_type == "direct_db":
                    rows = await DirectDBExecutor.execute_readonly(db_url, healed_sql, healed_params)
                else:
                    rows = await dispatcher.execute_sql(healed_sql, healed_params)
                sanitized_sql = healed_sql
                logger.info(f"Self-healing successfully auto-corrected query: {healed_sql}")
            except Exception as repair_err:
                logger.error(f"Self-healing reflection failed: {repair_err}")
                raise exec_err

        # 🛡️ Post-Execution Data Scrubber (SQL)
        if restricted_cols and rows:
            rows = [
                {k: v for k, v in r.items() if k.lower().strip() not in restricted_cols}
                if isinstance(r, dict) else r
                for r in rows
            ]

        return rows, sanitized_sql

    @classmethod
    async def _synthesize_response(
        cls,
        user_query: str,
        intent: str,
        sql_rows: Optional[List[Dict[str, Any]]],
        rag_chunks: Optional[List[Dict[str, Any]]],
        user_role: str,
        user_id: Optional[str] = None,
        guardrail_config: Optional[Dict[str, Any]] = None,
        agent_name: str = "Assistant",
        workspace_name: str = "Plug-N-Play AI"
    ) -> str:
        """Synthesizes structured records and/or RAG documents into a confident, authoritative, role-aware answer."""
        context_parts = []
        if sql_rows is not None and len(sql_rows) > 0:
            compact_rows = sql_rows[:10]
            rows_str = json.dumps(compact_rows, default=str)
            if len(rows_str) > 1500:
                rows_str = rows_str[:1500] + "..."
            context_parts.append(f"Operational Records:\n{rows_str}")

        if rag_chunks and len(rag_chunks) > 0:
            rag_text = "\n\n".join([f"[{c.get('metadata', {}).get('title', 'Document')}]:\n{c['content'][:1200]}" for c in rag_chunks[:4]])
            context_parts.append(f"Institutional Guidelines & Policies:\n{rag_text}")

        ctx = "\n\n".join(context_parts) if context_parts else "No specific records or document excerpts found matching the query."

        # 🎭 Role-Aware Context & Custom Instructions
        custom_role_hint = ""
        if guardrail_config and isinstance(guardrail_config.get("role_instructions"), dict):
            role_map = guardrail_config["role_instructions"]
            custom_inst = role_map.get(user_role.lower()) or role_map.get(user_role) or ""
            if custom_inst.strip():
                custom_role_hint = f"\n- Custom Instructions for Role '{user_role}':\n  {custom_inst.strip()}"

        role_section = f"""CURRENT USER CONTEXT & ROLE-BASED ACCESS CONTROL (RBAC):
- User Role: **{user_role}**
- User Identity / Auth ID: {user_id or 'anonymous'}
- Adapt your response tone, detail level, and scope to this role:
  * For end-users / students / customers: Use friendly, concise, and empowering language. Focus on their personal records, policies that affect them directly, and actionable next steps.
  * For staff / faculty / support: Use professional detail. Include operational metrics, cross-references, administrative context, and procedures.
  * For admin / management / executives: Provide full analytical depth, cross-table aggregate metrics, trends, and strategic insights.{custom_role_hint}
- Never reveal information, documents, or data columns that exceed this user's role permission boundary."""

        # 🛡️ GATE 3: Anti-Jailbreak and Safety Directives Injection
        safety_hint = ""
        if guardrail_config:
            instructions = guardrail_config.get("refusal_instructions") or []
            restricted_cols = guardrail_config.get("restricted_columns") or []
            hints = [f"- {inst}" for inst in instructions]
            if restricted_cols:
                hints.append(f"- Never reveal or discuss restricted personal columns: {', '.join(restricted_cols)}.")
            if hints:
                safety_hint = "\nCOMPLIANCE & PRIVACY RESTRICTIONS:\n" + "\n".join(hints)

        system_prompt = f"""You are {agent_name}, the official AI assistant representing the organization / company / workspace: **{workspace_name}**.

{role_section}

ORGANIZATION & WORKSPACE CONTEXT:
- Organization / Company / Workspace Name: **{workspace_name}**
- Assistant / Agent Name: **{agent_name}**
- If the user asks for the company name, workspace name, organization name, or who you represent:
  * State directly that your organization / workspace / company name is **{workspace_name}**.
  * State that you are {agent_name}, representing {workspace_name}.
  * If {workspace_name} is "Plug-N-Play AI" (or contains "Plug-N-Play"), explain that you represent the Plug-N-Play AI enterprise data and agent orchestration platform.
  * Inform the user that they can view or edit their profile and workspace information in the Account Center by clicking their profile avatar in the navigation bar.

CORE RESPONSE PRINCIPLES:
1. CONFIDENT & DIRECT (ZERO HEDGING):
   - Answer directly and authoritatively in the active voice as the representative of the organization.
   - NEVER start with or include robotic meta-disclaimers such as:
     * "According to the provided documents..."
     * "Based on the resources provided..."
     * "As per the database records..."
     * "The provided context indicates that..."
     * "In the documents uploaded..."
   - State the facts directly as established truth (e.g., state "Your attendance is 71.1%." rather than "Based on the records, your attendance is 71.1%.").

2. BOTTOM LINE UP FRONT (BLUF):
   - Deliver the direct answer, status, or ruling in the very first sentence.
   - Follow immediately with supporting criteria, metrics, or actionable next steps.

3. CLEAN VISUAL STRUCTURING:
   - Use clear markdown bullet points and bold highlights for critical numbers, thresholds, dates, and amounts.
   - If comparing operational data against policy rules (e.g. attendance vs requirement), format as a clear bulleted breakdown.
   - Do NOT use decorative separator lines like '***' or '---'.

4. ACTIONABLE GUIDANCE:
   - When a user has a shortfall, penalty, or restriction, explain the recommended next step (e.g. form submission, deadline, support escalation).

5. DECISIVE SCOPE HANDLING:
   - If information is not in the knowledge base, do not apologize or say "the document does not say". State clearly: "I don't have that information on file currently. Please click 'Support' below to connect with our team."
"""

        user_content = f"""Question: {user_query}

Context Information:
{ctx}{safety_hint}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        raw_answer = await LLMGateway.complete(messages, temperature=0.1, max_tokens=500)
        # Apply safety net regex cleaning
        return clean_hedging_prefix(raw_answer)

    @classmethod
    async def _stream_synthesize_response(
        cls,
        user_query: str,
        intent: str,
        sql_rows: Optional[List[Dict[str, Any]]],
        rag_chunks: Optional[List[Dict[str, Any]]],
        user_role: str,
        user_id: Optional[str] = None,
        guardrail_config: Optional[Dict[str, Any]] = None,
        agent_name: str = "Assistant",
        workspace_name: str = "Plug-N-Play AI"
    ) -> AsyncGenerator[str, None]:
        """Streaming token generator for synthesis response with real-time preamble scrubbing and role awareness."""
        context_parts = []
        if sql_rows is not None and len(sql_rows) > 0:
            compact_rows = sql_rows[:10]
            rows_str = json.dumps(compact_rows, default=str)
            if len(rows_str) > 1500:
                rows_str = rows_str[:1500] + "..."
            context_parts.append(f"Operational Records:\n{rows_str}")

        if rag_chunks and len(rag_chunks) > 0:
            rag_text = "\n\n".join([f"[{c.get('metadata', {}).get('title', 'Document')}]:\n{c['content'][:1200]}" for c in rag_chunks[:4]])
            context_parts.append(f"Institutional Guidelines & Policies:\n{rag_text}")

        ctx = "\n\n".join(context_parts) if context_parts else "No specific records or document excerpts found matching the query."

        # 🎭 Role-Aware Context & Custom Instructions
        custom_role_hint = ""
        if guardrail_config and isinstance(guardrail_config.get("role_instructions"), dict):
            role_map = guardrail_config["role_instructions"]
            custom_inst = role_map.get(user_role.lower()) or role_map.get(user_role) or ""
            if custom_inst.strip():
                custom_role_hint = f"\n- Custom Instructions for Role '{user_role}':\n  {custom_inst.strip()}"

        role_section = f"""CURRENT USER CONTEXT & ROLE-BASED ACCESS CONTROL (RBAC):
- User Role: **{user_role}**
- User Identity / Auth ID: {user_id or 'anonymous'}
- Adapt your response tone, detail level, and scope to this role:
  * For end-users / students / customers: Use friendly, concise, and empowering language. Focus on their personal records, policies that affect them directly, and actionable next steps.
  * For staff / faculty / support: Use professional detail. Include operational metrics, cross-references, administrative context, and procedures.
  * For admin / management / executives: Provide full analytical depth, cross-table aggregate metrics, trends, and strategic insights.{custom_role_hint}
- Never reveal information, documents, or data columns that exceed this user's role permission boundary."""

        safety_hint = ""
        if guardrail_config:
            instructions = guardrail_config.get("refusal_instructions") or []
            restricted_cols = guardrail_config.get("restricted_columns") or []
            hints = [f"- {inst}" for inst in instructions]
            if restricted_cols:
                hints.append(f"- Never reveal or discuss restricted personal columns: {', '.join(restricted_cols)}.")
            if hints:
                safety_hint = "\nCOMPLIANCE & PRIVACY RESTRICTIONS:\n" + "\n".join(hints)

        system_prompt = f"""You are {agent_name}, the official AI assistant representing the organization / company / workspace: **{workspace_name}**.

{role_section}

ORGANIZATION & WORKSPACE CONTEXT:
- Organization / Company / Workspace Name: **{workspace_name}**
- Assistant / Agent Name: **{agent_name}**
- If the user asks for the company name, workspace name, organization name, or who you represent:
  * State directly that your organization / workspace / company name is **{workspace_name}**.
  * State that you are {agent_name}, representing {workspace_name}.
  * If {workspace_name} is "Plug-N-Play AI" (or contains "Plug-N-Play"), explain that you represent the Plug-N-Play AI enterprise data and agent orchestration platform.
  * Inform the user that they can view or edit their profile and workspace information in the Account Center by clicking their profile avatar in the navigation bar.

CORE RESPONSE PRINCIPLES:
1. CONFIDENT & DIRECT (ZERO HEDGING):
   - Answer directly and authoritatively in the active voice as the representative of the organization.
   - NEVER start with or include robotic meta-disclaimers such as:
     * "According to the provided documents..."
     * "Based on the resources provided..."
     * "As per the database records..."
     * "The provided context indicates that..."
     * "In the documents uploaded..."
   - State the facts directly as established truth (e.g., state "Your attendance is 71.1%." rather than "Based on the records, your attendance is 71.1%.").

2. BOTTOM LINE UP FRONT (BLUF):
   - Deliver the direct answer, status, or ruling in the very first sentence.
   - Follow immediately with supporting criteria, metrics, or actionable next steps.

3. CLEAN VISUAL STRUCTURING:
   - Use clear markdown bullet points and bold highlights for critical numbers, thresholds, dates, and amounts.
   - If comparing operational data against policy rules (e.g. attendance vs requirement), format as a clear bulleted breakdown.
   - Do NOT use decorative separator lines like '***' or '---'.

4. ACTIONABLE GUIDANCE:
   - When a user has a shortfall, penalty, or restriction, explain the recommended next step (e.g. form submission, deadline, support escalation).

5. DECISIVE SCOPE HANDLING:
   - If information is not in the knowledge base, do not apologize or say "the document does not say". State clearly: "I don't have that information on file currently. Please click 'Support' below to connect with our team."
"""

        user_content = f"""Question: {user_query}

Context Information:
{ctx}{safety_hint}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        # Streaming with Real-Time Preamble Scrubbing Buffer
        # Buffer first ~65 characters to catch and strip any opening hedging disclaimer
        preamble_buffer = ""
        preamble_flushed = False
        BUFFER_SIZE = 65

        async for token in LLMGateway.stream(messages, temperature=0.1, max_tokens=500):
            if not preamble_flushed:
                preamble_buffer += token
                if len(preamble_buffer) >= BUFFER_SIZE or "\n" in preamble_buffer or (". " in preamble_buffer and len(preamble_buffer) > 20):
                    cleaned_preamble = clean_hedging_prefix(preamble_buffer, preserve_trailing_space=True)
                    preamble_flushed = True
                    if cleaned_preamble:
                        yield cleaned_preamble
            else:
                yield token

        # If stream ended before buffer reached threshold
        if not preamble_flushed and preamble_buffer:
            cleaned_preamble = clean_hedging_prefix(preamble_buffer, preserve_trailing_space=False)
            if cleaned_preamble:
                yield cleaned_preamble

    @classmethod
    async def stream_query(
        cls,
        db: AsyncSession,
        session: ChatSession,
        user_query: str
    ) -> AsyncGenerator[str, None]:
        """
        Streaming generator for Server-Sent Events (SSE).
        Yields JSON packets formatted for SSE:
        - data: {"event": "meta", ...}
        - data: {"event": "token", "token": "..."}
        - data: {"event": "done", "message_id": "...", ...}
        """
        start_time = time.time()
        tenant_id = session.tenant_id
        user_role = session.user_role or "user"
        external_user_id = session.external_user_id

        # 💳 Quota & Billing Check
        tenant = await db.get(Tenant, tenant_id)
        if tenant:
            limit = tenant.monthly_query_limit or 150
            used = tenant.queries_used_this_month or 0
            if used >= limit:
                refusal_msg = f"This AI Assistant has reached its monthly allowance of {limit} queries. Please upgrade your plan in the Plug-N-Play AI dashboard to resume responses."
                yield f"data: {json.dumps({'event': 'meta', 'route': 'QUOTA_EXCEEDED', 'quota_exceeded': True})}\n\n"
                yield f"data: {json.dumps({'event': 'token', 'token': refusal_msg})}\n\n"
                yield f"data: {json.dumps({'event': 'done', 'quota_exceeded': True})}\n\n"
                return
            tenant.queries_used_this_month = used + 1

        # 0. Check Redis Cache
        cached_result = await RedisService.get_query_cache(
            agent_id=session.agent_id,
            user_role=user_role,
            user_id=external_user_id,
            query=user_query
        )
        if cached_result:
            yield f"data: {json.dumps({'event': 'meta', 'route': cached_result.get('route_chosen'), 'generated_sql': cached_result.get('generated_sql'), 'rag_sources': cached_result.get('rag_sources'), 'cached': True})}\n\n"
            # Stream cached answer
            words = cached_result.get("answer", "").split(" ")
            for i, word in enumerate(words):
                w = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'event': 'token', 'token': w})}\n\n"
                await asyncio.sleep(0.01)

            # Record message
            asst_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=cached_result.get("answer", ""),
                metadata_json={"route_chosen": cached_result.get("route_chosen"), "cached": True}
            )
            db.add(asst_msg)
            await db.commit()
            await db.refresh(asst_msg)

            yield f"data: {json.dumps({'event': 'done', 'message_id': asst_msg.id, 'total_ms': int((time.time() - start_time) * 1000)})}\n\n"
            return

        # Fetch Agent & Guardrails
        agent_stmt = select(Agent).where(Agent.id == session.agent_id)
        agent_res = await db.execute(agent_stmt)
        agent = agent_res.scalars().first()
        guardrail_config = None
        if agent and agent.guardrail_config:
            try:
                guardrail_config = json.loads(agent.guardrail_config)
            except Exception:
                pass

        # Multi-Turn Contextualization
        effective_query = await QueryContextualizer.contextualize_query(db, session.id, user_query)

        # Gate 1 Guardrails
        is_blocked, refusal_msg = AIGuardrailCompiler.evaluate_query(effective_query, guardrail_config, user_role=user_role)
        if not is_blocked and effective_query != user_query:
            is_blocked, refusal_msg = AIGuardrailCompiler.evaluate_query(user_query, guardrail_config, user_role=user_role)

        if is_blocked:
            refusal = refusal_msg or "I cannot assist with this request due to platform safety restrictions."
            yield f"data: {json.dumps({'event': 'meta', 'route': 'GUARDRAIL_BLOCKED', 'guardrail_blocked': True, 'generated_sql': None, 'rag_sources': None, 'cached': False})}\n\n"
            
            words = refusal.split(" ")
            for i, word in enumerate(words):
                w = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'event': 'token', 'token': w})}\n\n"
                await asyncio.sleep(0.01)

            asst_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=refusal,
                metadata_json={"route_chosen": "GUARDRAIL_BLOCKED"}
            )
            db.add(asst_msg)
            
            query_log = QueryLog(
                tenant_id=tenant_id,
                session_id=session.id,
                user_query=user_query,
                route_chosen="GUARDRAIL_BLOCKED",
                llm_generation_ms=1,
                total_tokens=len(user_query.split()) + len(refusal.split()),
                error_message=None
            )
            db.add(query_log)
            await db.commit()
            await db.refresh(asst_msg)

            yield f"data: {json.dumps({'event': 'done', 'message_id': asst_msg.id, 'total_ms': int((time.time() - start_time) * 1000)})}\n\n"
            return

        # ⚡ ACTION & TOOL LAYER: Check for executable action intent in streaming mode
        if session.agent_id:
            act_stmt = select(ActionDefinition).where(
                ActionDefinition.agent_id == session.agent_id,
                ActionDefinition.is_active == True
            )
            act_res = await db.execute(act_stmt)
            active_actions = act_res.scalars().all()
            if active_actions:
                detected = await ActionToolCompiler.detect_action_intent(
                    query=effective_query,
                    actions=active_actions,
                    user_role=user_role
                )
                if detected:
                    action, extracted_params = detected
                    agent_name = agent.name if agent else "Plug-N-Play AI"
                    if action.requires_user_confirmation:
                        proposal = {
                            "action_id": action.id,
                            "name": action.name,
                            "display_name": action.display_name,
                            "parameters": extracted_params,
                            "requires_confirmation": True,
                            "execution_target": getattr(action, "execution_target", "server") or "server",
                            "endpoint_url": action.endpoint_url,
                            "http_method": (action.http_method or "POST").upper(),
                            "client_event_name": getattr(action, "client_event_name", None)
                        }
                        ans = f"I have prepared your request to **{action.display_name}**. Please review the details below and confirm to proceed."
                        yield f"data: {json.dumps({'event': 'meta', 'route': 'ACTION_PROPOSAL', 'cached': False})}\n\n"
                        yield f"data: {json.dumps({'event': 'action_proposal', **proposal})}\n\n"
                        
                        words = ans.split(" ")
                        for i, w in enumerate(words):
                            token = w + (" " if i < len(words) - 1 else "")
                            yield f"data: {json.dumps({'event': 'token', 'token': token})}\n\n"
                            await asyncio.sleep(0.01)
                            
                        asst_msg = ChatMessage(
                            session_id=session.id,
                            role="assistant",
                            content=ans,
                            metadata_json={"route_chosen": "ACTION_PROPOSAL", "action_proposal": proposal}
                        )
                        db.add(asst_msg)
                        query_log = QueryLog(
                            tenant_id=tenant_id,
                            session_id=session.id,
                            user_query=user_query,
                            route_chosen="ACTION_PROPOSAL",
                            total_tokens=len(user_query.split()) + len(ans.split())
                        )
                        db.add(query_log)
                        await db.commit()
                        await db.refresh(asst_msg)
                        
                        yield f"data: {json.dumps({'event': 'done', 'message_id': asst_msg.id, 'action_proposal': proposal, 'total_ms': int((time.time() - start_time) * 1000)})}\n\n"
                        return
                    else:
                        exec_res = await ActionDispatcher.dispatch_action(
                            action=action,
                            parameters=extracted_params,
                            tenant_id=tenant_id,
                            external_user_id=external_user_id,
                            session_id=session.id,
                            db=db,
                            agent_name=agent_name
                        )
                        yield f"data: {json.dumps({'event': 'meta', 'route': 'ACTION_EXECUTED', 'cached': False})}\n\n"
                        words = exec_res.natural_confirmation.split(" ")
                        for i, w in enumerate(words):
                            token = w + (" " if i < len(words) - 1 else "")
                            yield f"data: {json.dumps({'event': 'token', 'token': token})}\n\n"
                            await asyncio.sleep(0.01)
                            
                        asst_msg = ChatMessage(
                            session_id=session.id,
                            role="assistant",
                            content=exec_res.natural_confirmation,
                            metadata_json={"route_chosen": "ACTION_EXECUTED"}
                        )
                        db.add(asst_msg)
                        query_log = QueryLog(
                            tenant_id=tenant_id,
                            session_id=session.id,
                            user_query=user_query,
                            route_chosen="ACTION_EXECUTED",
                            total_tokens=len(user_query.split()) + len(exec_res.natural_confirmation.split())
                        )
                        db.add(query_log)
                        await db.commit()
                        await db.refresh(asst_msg)
                        
                        yield f"data: {json.dumps({'event': 'done', 'message_id': asst_msg.id, 'total_ms': int((time.time() - start_time) * 1000)})}\n\n"
                        return

        # Intent Routing with Agent Service Type Awareness
        if agent and agent.description and agent.description.upper().startswith("RAG"):
            intent, route_reason = "RAG", "Agent configured strictly for Document RAG"
        elif agent and agent.description and agent.description.upper().startswith("SQL"):
            intent, route_reason = "SQL", "Agent configured strictly for Text-to-SQL"
        else:
            intent, route_reason = await IntentRouter.route_query(effective_query)
        sql_rows = None
        rag_chunks = None
        generated_sql = None
        sql_time_ms = 0
        rag_time_ms = 0
        llm_time_ms = 0

        # Execute data pipelines
        if intent in {"SQL", "HYBRID"}:
            try:
                t0 = time.time()
                sql_rows, generated_sql = await cls._execute_sql_pipeline(
                    db, tenant_id, effective_query, external_user_id, user_role, guardrail_config
                )
                sql_time_ms = int((time.time() - t0) * 1000)
            except Exception as e:
                logger.info(f"SQL execution error or no DB ({e}), falling back to RAG")
                sql_rows = None

        # Always retrieve RAG if intent is RAG/HYBRID or if SQL returned empty/no records
        if intent in {"RAG", "HYBRID"} or not sql_rows:
            try:
                t0 = time.time()
                rag_chunks = await RAGRetriever.retrieve_relevant_chunks(
                    db, tenant_id, effective_query, user_role=user_role, top_k=4
                )
                rag_time_ms = int((time.time() - t0) * 1000)
                if rag_chunks and not sql_rows and intent == "SQL":
                    intent = "RAG"
            except Exception as e:
                logger.error(f"RAG retrieval error: {e}")

        # Emit Metadata Event
        yield f"data: {json.dumps({'event': 'meta', 'route': intent, 'generated_sql': generated_sql, 'rag_sources': rag_chunks, 'cached': False})}\n\n"

        # Stream LLM tokens
        full_answer_parts = []
        t0 = time.time()
        try:
            agent_name = agent.name if agent else "Plug-N-Play AI"
            workspace_name = tenant.name if (tenant and tenant.name) else "Plug-N-Play AI"
            async for token in cls._stream_synthesize_response(
                user_query=effective_query,
                intent=intent,
                sql_rows=sql_rows,
                rag_chunks=rag_chunks,
                user_role=user_role,
                user_id=external_user_id,
                guardrail_config=guardrail_config,
                agent_name=agent_name,
                workspace_name=workspace_name
            ):
                full_answer_parts.append(token)
                yield f"data: {json.dumps({'event': 'token', 'token': token})}\n\n"
        except Exception as e:
            err_msg = f"\n[Streaming error: {e}]"
            full_answer_parts.append(err_msg)
            yield f"data: {json.dumps({'event': 'token', 'token': err_msg})}\n\n"

        llm_time_ms = int((time.time() - t0) * 1000)
        full_answer = "".join(full_answer_parts)

        # Save assistant message & telemetry
        asst_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=full_answer,
            metadata_json={"route_chosen": intent, "generated_sql": generated_sql}
        )
        db.add(asst_msg)

        query_log = QueryLog(
            tenant_id=tenant_id,
            session_id=session.id,
            user_query=user_query,
            route_chosen=intent,
            generated_sql=generated_sql,
            sql_execution_ms=sql_time_ms,
            rag_retrieval_ms=rag_time_ms,
            llm_generation_ms=llm_time_ms,
            total_tokens=len(user_query.split()) + len(full_answer.split())
        )
        db.add(query_log)
        await db.commit()
        await db.refresh(asst_msg)

        # Cache in Redis
        if full_answer:
            await RedisService.set_query_cache(
                agent_id=session.agent_id,
                user_role=user_role,
                user_id=external_user_id,
                query=user_query,
                response_data={
                    "answer": full_answer,
                    "route_chosen": intent,
                    "structured_data": sql_rows,
                    "rag_sources": rag_chunks,
                    "generated_sql": generated_sql,
                    "session_id": session.id,
                    "cached": False
                },
                ttl=300
            )

        yield f"data: {json.dumps({'event': 'done', 'message_id': asst_msg.id, 'total_ms': int((time.time() - start_time) * 1000)})}\n\n"

