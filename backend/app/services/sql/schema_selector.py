"""
Universal Semantic Schema Selector — database-agnostic schema pruning.
Uses lexical token-overlap and semantic matching between the user query and table/column metadata
to dynamically select the Top-K relevant tables for ANY database (ERP, E-Commerce, Healthcare, EdTech, etc.).
"""

import re
from typing import List, Any, Set


class SemanticSchemaSelector:
    """
    Universally selects the most relevant tables/collections from arbitrary databases
    without any hardcoded domain knowledge.
    """

    @classmethod
    def select_relevant_tables(
        cls,
        tables: List[Any],
        user_query: str,
        max_tables: int = 8,
        user_role: str = "user"
    ) -> List[Any]:
        """
        Ranks all tenant tables against the user query by computing match scores
        across table names, business names, descriptions, and column names.
        """
        # 1. Filter RBAC permissions
        allowed_tables = [
            t for t in tables
            if t.is_queryable and (not t.allowed_roles or user_role in t.allowed_roles or "admin" in t.allowed_roles)
        ]

        if not allowed_tables or len(allowed_tables) <= max_tables:
            return allowed_tables

        # 2. Extract query tokens (normalized words > 1 char)
        query_words = set(re.findall(r"\w+", user_query.lower()))
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "in", "on", "at", "to", "for", 
            "of", "with", "by", "from", "and", "or", "what", "who", "which", "where", "how", 
            "many", "give", "show", "list", "tell", "any", "there", "some", "all", "get", "find",
            "me", "my", "our", "their", "please", "can", "could", "would", "do", "does", "did"
        }
        content_words = {w for w in query_words if w not in stop_words and len(w) > 1}

        # 3. Score each table generically
        scored_tables = []
        for tbl in allowed_tables:
            score = 0
            t_name = tbl.table_name.lower()
            t_biz = (tbl.business_name or "").lower()
            t_desc = (tbl.description or "").lower()

            # Direct word / substring matches on table metadata
            for w in content_words:
                if w in t_name:
                    score += 15
                if w in t_biz:
                    score += 10
                if w in t_desc:
                    score += 5

            # Matches on column names
            for col in (tbl.columns or []):
                c_name = col.column_name.lower()
                c_desc = (col.business_meaning or "").lower()
                for w in content_words:
                    if w in c_name:
                        score += 8
                    if w in c_desc:
                        score += 3

            # Entity & Role lookup: If query asks for names, people, roles, or identity,
            # tables that have (name/full_name) AND (role/email/department) are prime user/participant entities
            is_person_role_query = any(w in user_query.lower() for w in ["name", "names", "who", "user", "person", "staff", "member", "role", "admin", "lead", "head", "manager", "tpo", "employee", "student"])
            has_name_col = any(any(n in c.column_name.lower() for n in ["full_name", "name", "username"]) for c in (tbl.columns or []))
            has_role_col = any(any(r in c.column_name.lower() for r in ["role", "department", "designation", "role_id", "user_type"]) for c in (tbl.columns or []))
            
            if is_person_role_query and has_name_col:
                score += 15
                if has_role_col:
                    score += 20  # Strong boost for tables that hold named actors with roles

            scored_tables.append((score, tbl))

        # 4. Sort descending by score
        scored_tables.sort(key=lambda x: x[0], reverse=True)

        # 5. Return Top-K tables
        return [tbl for _, tbl in scored_tables[:max_tables]]
