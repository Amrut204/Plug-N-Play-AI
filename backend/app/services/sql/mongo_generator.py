"""
Text-to-MQL Engine — generates MongoDB aggregation pipelines from natural language.
Parallel to TextToSQLEngine but for MongoDB collections instead of SQL tables.
"""

import json
import logging
from typing import List, Any, Optional, Set, Tuple, Dict

from app.services.sql.schema_selector import SemanticSchemaSelector

logger = logging.getLogger(__name__)


class TextToMQLEngine:
    """
    Universal Text-to-MQL Engine — translates natural language questions into safe MongoDB
    aggregation pipelines for ANY database schema (E-Commerce, ERP, Healthcare, Education, etc.).
    """

    @classmethod
    def build_schema_context(
        cls, 
        tables: List[Any], 
        user_role: str = "user", 
        user_query: str = "", 
        max_chars: int = 2500,
        restricted_columns: Optional[Set[str]] = None
    ) -> str:
        """
        Dynamically selects the most relevant collections for the user's query
        using universal semantic scoring, then renders a compact signature,
        strictly purging sensitive and guardrail-restricted fields.
        """
        relevant_tables = SemanticSchemaSelector.select_relevant_tables(
            tables=tables,
            user_query=user_query,
            max_tables=10,
            user_role=user_role
        )

        restricted = {c.lower().strip() for c in (restricted_columns or set())}

        schema_lines = []
        total_chars = 0
        for tbl in relevant_tables:
            fields = []
            for col in (tbl.columns or []):
                col_name = str(col.column_name).strip()
                if getattr(col, 'is_sensitive', False) or col_name.lower() in restricted:
                    continue
                fields.append(col_name)

            line = f"{tbl.table_name}({', '.join(fields[:15])})"
            total_chars += len(line)
            if total_chars > max_chars:
                break
            schema_lines.append(line)

        return "\n".join(schema_lines)

    @classmethod
    def create_mql_prompt(
        cls,
        user_query: str,
        schema_context: str,
        user_id: Optional[str] = None,
        user_role: str = "user"
    ) -> str:
        """
        Constructs a universal Text-to-MQL prompt without any domain-specific hardcoding.
        """
        return f"""Generate a safe, read-only MongoDB aggregation pipeline. Output JSON in a ```json``` block with keys "collection" and "pipeline".
Rules:
1. Use the EXACT collection and field names from the SCHEMA below.
2. If the user asks for 'names', people, or entities, select the collection that actually contains a name/title column (e.g. full_name, name, title) rather than event, log, or run collections.
3. If the user asks for entities with a specific role, title, category, or status (e.g. 'manager', 'tpo', 'doctor', 'active', 'pending'), query the main entity collection (e.g. users, members, accounts, items) filtering on the corresponding role/type/category field (e.g. {{"role": "tpo"}} or {{"status": "active"}}).
4. For text/string searches or names, use case-insensitive regex: {{"$regex": "...", "$options": "i"}}.
5. Limit results to at most 20 documents if no specific count/aggregation is requested.
6. Only use read operations ($match, $group, $sort, $limit, $project, $count, $unwind). Never write or mutate.

SCHEMA:
{schema_context}

User ID: {user_id or 'anonymous'} | Role: {user_role}

Question: {user_query}"""

    @classmethod
    def extract_and_validate(
        cls,
        raw_llm_response: str,
        allowed_collections: Set[str]
    ) -> Tuple[str, list]:
        """
        Extracts the MongoDB query from the LLM response and validates it.
        Returns (collection_name, pipeline).
        """
        content = raw_llm_response.strip()

        # Extract JSON from code block
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        try:
            query = json.loads(content)
        except json.JSONDecodeError as e:
            # Fallback: attempt to find first JSON object { ... }
            try:
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1:
                    query = json.loads(content[start:end+1])
                else:
                    raise ValueError(f"Could not parse JSON from LLM: {e}")
            except Exception:
                raise ValueError(f"LLM returned invalid JSON: {e}")

        collection = None
        pipeline = []

        if isinstance(query, dict):
            collection = query.get("collection") or query.get("table") or query.get("collection_name")
            raw_pipeline = query.get("pipeline") or query.get("stages") or query.get("aggregation")

            if raw_pipeline is None:
                # LLM might have returned a find() filter like {"filter": {"dept": "HR"}}
                flt = query.get("filter") or query.get("query") or query.get("find") or {}
                if isinstance(flt, dict):
                    pipeline = [{"$match": flt}] if flt else []
                else:
                    pipeline = []
            elif isinstance(raw_pipeline, list):
                pipeline = raw_pipeline
            elif isinstance(raw_pipeline, dict):
                pipeline = [raw_pipeline]
            else:
                pipeline = []
        elif isinstance(query, list):
            # LLM returned just an array of stages
            pipeline = query

        # Case-insensitive collection name matching against allowed collections
        target_collection = None
        if collection:
            for ac in allowed_collections:
                if ac.lower() == str(collection).lower():
                    target_collection = ac
                    break

        if not target_collection and allowed_collections:
            # If single collection whitelisted or exact match not found, default to first match
            target_collection = next(iter(allowed_collections))

        if not target_collection:
            raise ValueError(f"Could not identify a valid collection. Allowed: {allowed_collections}")

        # Validate no write operations in pipeline
        dangerous_stages = {"$out", "$merge", "$write", "$delete"}
        for stage in pipeline:
            if isinstance(stage, dict):
                for key in stage:
                    if key in dangerous_stages:
                        raise ValueError(f"Blocked dangerous MongoDB operation: {key}")

        return target_collection, pipeline
