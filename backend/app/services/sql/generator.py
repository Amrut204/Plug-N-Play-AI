from typing import List, Dict, Any, Optional, Tuple, Set
from app.services.sql.validator import SQLASTValidator, SQLSecurityViolation
import logging

from app.services.sql.schema_selector import SemanticSchemaSelector

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return len(text) // 4


class TextToSQLEngine:
    """
    Universal Text-to-SQL Engine — translates natural language questions into safe,
    read-only SQL queries for ANY database schema (PostgreSQL, MySQL, SQLite, Snowflake, etc.).
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
        Dynamically selects the most relevant tables for the user's query
        using universal semantic scoring, then renders a compact signature,
        strictly purging sensitive and guardrail-restricted columns.
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
            cols = []
            for col in (tbl.columns or []):
                col_name = str(col.column_name).strip()
                if getattr(col, 'is_sensitive', False) or col_name.lower() in restricted:
                    continue
                cols.append(col_name)

            line = f"{tbl.table_name}({', '.join(cols[:15])})"
            total_chars += len(line)
            if total_chars > max_chars:
                break
            schema_lines.append(line)

        return "\n".join(schema_lines)

    @classmethod
    def create_sql_prompt(
        cls, 
        user_query: str, 
        schema_context: str, 
        user_id: Optional[str] = None, 
        user_role: str = "user",
        dialect: str = "postgres"
    ) -> str:
        """
        Constructs a universal Text-to-SQL prompt with relational JOIN awareness and fuzzy matching.
        """
        match_rule = "Use ILIKE '%value%'" if dialect == "postgres" else "Use LIKE '%value%' or LOWER(col) LIKE '%value%'"
        return f"""Generate a safe, read-only SELECT query for this question. Output ONLY raw SQL in a ```sql``` block.
Rules:
1. Output ONLY a valid SELECT statement. Never INSERT, UPDATE, DELETE, DROP, or ALTER.
2. Use EXACT table and column names from the SCHEMA below.
3. For multi-table queries, perform standard JOINs on matching foreign keys (e.g. table_a.user_id = users.id).
4. For string/name searching or filtering, {match_rule} to ensure case-insensitive and partial typo tolerance.
5. If the user asks for entities with a specific role, title, category, or status (e.g. 'manager', 'tpo', 'doctor', 'active', 'pending'), query the main entity table filtering on the corresponding role/type/category column.
6. Limit results to at most 20 rows if no specific count is requested.
7. If the question refers to the current user (e.g. 'my orders', 'my attendance', 'my grades', 'my prn', 'my cgpa', 'my profile', 'my account', 'my balance') and User ID is provided (not anonymous): if User ID is a name or contains letters/spaces (e.g. '{user_id}'), filter flexibly by matching against the name, PRN, or student identifier column (e.g. WHERE (name ILIKE '%{user_id}%' OR student_id = '{user_id}' OR prn = '{user_id}')); if User ID is an ID code, match against the ID or PRN column.
8. If the user has an elevated management role (e.g. 'tpo', 'faculty', 'admin', 'management') and asks for student performance (e.g. a specific student's CGPA, attendance, marks, or students meeting placement eligibility criteria like CGPA >= 7.0), query across the student table filtering on the target student or criteria without restricting to the requester's own User ID.

SCHEMA:
{schema_context}

User ID: {user_id or 'anonymous'} | Role: {user_role}

Question: {user_query}"""

    @classmethod
    def extract_and_validate(
        cls,
        raw_llm_response: str,
        allowed_tables: Set[str],
        allowed_columns: Optional[Dict[str, Set[str]]] = None,
        identity_filter: Optional[Tuple[str, str, Any]] = None,
        dialect: str = "postgres"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Extracts SQL code block from LLM response and runs AST validation.
        """
        # Find ```sql block or strip
        content = raw_llm_response.strip()
        if "```sql" in content:
            content = content.split("```sql")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return SQLASTValidator.validate_and_sanitize(
            raw_sql=content,
            allowed_tables=allowed_tables,
            allowed_columns=allowed_columns,
            identity_filter=identity_filter,
            dialect=dialect
        )

    @classmethod
    def create_sql_repair_prompt(
        cls,
        user_query: str,
        failed_sql: str,
        error_message: str,
        schema_context: str,
        dialect: str = "postgres"
    ) -> str:
        """
        Constructs a targeted self-healing prompt with the exact database runtime error.
        """
        match_rule = "Use ILIKE '%value%'" if dialect == "postgres" else "Use LIKE '%value%' or LOWER(col) LIKE '%value%'"
        return f"""The previous SQL query failed during execution on the database. Repair and fix the SQL query. Output ONLY the corrected raw SQL inside a ```sql``` block.

SCHEMA:
{schema_context}

Question: {user_query}
Failed SQL: {failed_sql}
Database Error: {error_message}

Rules:
1. Fix the error by strictly referencing valid column and table names from the SCHEMA.
2. Output ONLY a valid SELECT statement. Never INSERT, UPDATE, DELETE, DROP, or ALTER.
3. {match_rule} for string matching.
4. Limit results to at most 20 rows."""

