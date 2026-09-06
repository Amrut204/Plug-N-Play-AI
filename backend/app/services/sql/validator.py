import sqlglot
from sqlglot import exp
from typing import List, Dict, Set, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class SQLSecurityViolation(Exception):
    """Raised when generated SQL violates safety constraints."""
    pass


class SQLASTValidator:
    """
    Independent AST-based SQL Validator.
    The LLM is NEVER the security boundary. All generated queries
    must pass through this validator before reaching any database or connector.
    """

    FORBIDDEN_EXPRESSIONS = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Alter,
        exp.Create,
        exp.Command,
        exp.TruncateTable,
    )

    SYSTEM_BLACKLIST_TABLES = {
        "alembic_version", "tenants", "users", "agents", "connections",
        "semantic_tables", "semantic_columns", "rag_sources", "rag_chunks",
        "chat_sessions", "chat_messages", "query_logs", "action_definitions"
    }

    @classmethod
    def validate_and_sanitize(
        cls,
        raw_sql: str,
        allowed_tables: Set[str],
        allowed_columns: Optional[Dict[str, Set[str]]] = None,
        identity_filter: Optional[Tuple[str, str, Any]] = None, # (table_name, column_name, value)
        max_limit: int = 50,
        dialect: str = "postgres"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Parses SQL AST, verifies read-only access, validates table/column whitelists,
        injects identity constraints, and clamps LIMIT clauses.
        
        Returns:
            (sanitized_sql, bound_parameters)
        """
        # Clean markdown wrappers if present
        sql_clean = raw_sql.strip()
        if sql_clean.startswith("```"):
            lines = sql_clean.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            sql_clean = "\n".join(lines).strip()

        # Parse statements
        try:
            parsed_statements = sqlglot.parse(sql_clean, read=dialect)
        except Exception as e:
            raise SQLSecurityViolation(f"SQL Syntax Error / Unparseable Query: {e}")

        if not parsed_statements:
            raise SQLSecurityViolation("Empty SQL query")

        if len(parsed_statements) > 1:
            raise SQLSecurityViolation("Multiple SQL statements are strictly forbidden")

        expression = parsed_statements[0]

        # 1. Rule: Must be a Select query
        if not isinstance(expression, exp.Select):
            raise SQLSecurityViolation(
                f"Forbidden statement type: only SELECT queries are permitted. Found {type(expression).__name__}"
            )

        # 2. Rule: Check for any nested write/modify operations
        for forbidden in cls.FORBIDDEN_EXPRESSIONS:
            if expression.find(forbidden):
                raise SQLSecurityViolation(f"Forbidden operation detected: {forbidden.__name__}")

        # 3. Rule: Validate whitelisted tables & protect internal platform tables
        referenced_tables = {
            t.name.lower() 
            for t in expression.find_all(exp.Table) 
            if t.name
        }
        allowed_tables_lower = {t.lower() for t in allowed_tables}

        for tbl in referenced_tables:
            if tbl in cls.SYSTEM_BLACKLIST_TABLES:
                raise SQLSecurityViolation(f"Access to internal system table '{tbl}' is strictly prohibited.")
            if tbl not in allowed_tables_lower:
                raise SQLSecurityViolation(f"Access to table '{tbl}' is not permitted for this role")

        # 4. Rule: Validate columns (if column dictionary provided)
        if allowed_columns:
            for col in expression.find_all(exp.Column):
                col_name = col.name.lower()
                table_name = col.table.lower() if col.table else None
                if table_name:
                    if table_name in allowed_columns:
                        if col_name not in {c.lower() for c in allowed_columns[table_name]}:
                            raise SQLSecurityViolation(f"Access to column '{table_name}.{col_name}' is forbidden")
                else:
                    # Unqualified column: must exist in at least one referenced table's allowed columns
                    all_allowed_for_query = set()
                    for tbl in referenced_tables:
                        if tbl in allowed_columns:
                            all_allowed_for_query.update({c.lower() for c in allowed_columns[tbl]})
                    if all_allowed_for_query and col_name not in all_allowed_for_query:
                        raise SQLSecurityViolation(f"Access to column '{col_name}' is forbidden")

        # 5. Rule: Enforce LIMIT
        limit_expr = expression.find(exp.Limit)
        if not limit_expr:
            expression = expression.limit(max_limit)
        else:
            try:
                current_limit = int(limit_expr.expression.this)
                if current_limit > max_limit:
                    expression.set("limit", exp.Limit(expression=exp.Literal.number(max_limit)))
            except Exception:
                expression.set("limit", exp.Limit(expression=exp.Literal.number(max_limit)))

        # 6. Rule: Inject Row-Level Security / Identity Constraints
        bound_params: Dict[str, Any] = {}
        if identity_filter:
            target_table, target_col, user_value = identity_filter
            param_key = f"auth_{target_col}"
            bound_params[param_key] = user_value
            bound_params["auth_user_id"] = user_value
            bound_params[target_col] = user_value
            
            # If target table is queried and doesn't already have an equality check on target_col, enforce WHERE
            if target_table.lower() in referenced_tables:
                where_clause = f"{target_table}.{target_col} = :{param_key}"
                # Check if expression already has a where condition on target_col or user identity
                existing_where = expression.find(exp.Where)
                where_str = existing_where.sql() if existing_where else ""
                user_val_str = str(user_value).lower().strip()
                already_filtered = (
                    target_col.lower() in where_str.lower() or 
                    (bool(user_val_str) and user_val_str in where_str.lower())
                )
                if not already_filtered:
                    expression = expression.where(where_clause, append=True)

        sanitized_sql = expression.sql(dialect=dialect)
        # Normalize %(param)s to :param for universal DB-API compatibility across SQLite and Postgres
        import re
        sanitized_sql = re.sub(r"%\((\w+)\)s", r":\1", sanitized_sql)
        return sanitized_sql, bound_params
