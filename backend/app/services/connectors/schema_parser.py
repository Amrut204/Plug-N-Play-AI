import re
import json
from typing import Dict, List, Any


class SchemaDDLParser:
    """
    Parses SQL DDL, Prisma Schema, or JSON definitions into structured
    Semantic Tables & Columns without connecting to any external database.
    Zero-Knowledge: No credentials or host URLs required.
    """

    @classmethod
    def parse(cls, raw_schema: str) -> List[Dict[str, Any]]:
        text = (raw_schema or "").strip()
        if not text:
            return []

        # Try JSON first
        if text.startswith("{") or text.startswith("["):
            try:
                parsed_json = json.loads(text)
                return cls._parse_json(parsed_json)
            except Exception:
                pass

        # Try Prisma model format
        if "model " in text and "{" in text:
            return cls._parse_prisma(text)

        # Default: SQL DDL parser (CREATE TABLE ...)
        return cls._parse_sql_ddl(text)

    @classmethod
    def _parse_sql_ddl(cls, text: str) -> List[Dict[str, Any]]:
        tables = []
        # Match CREATE TABLE [IF NOT EXISTS] [schema.]table_name (...)
        table_pattern = re.compile(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:[\"\`\w]+\.)?[\"\`]?(\w+)[\"\`]?\s*\((.*?)\)(?:\s*;|\s*$)",
            re.IGNORECASE | re.DOTALL
        )

        matches = list(table_pattern.finditer(text))
        if matches:
            for match in matches:
                tbl_name = match.group(1).strip().lower()
                body = match.group(2).strip()

                cols = []
                # Split by commas that are not inside parentheses
                lines = cls._split_sql_column_lines(body)
                for line in lines:
                    line = line.strip().rstrip(",")
                    if not line:
                        continue
                    # Ignore table constraints (PRIMARY KEY (...), FOREIGN KEY (...), CONSTRAINT, CHECK, UNIQUE)
                    upper = line.upper()
                    if upper.startswith(("PRIMARY KEY", "FOREIGN KEY", "CONSTRAINT", "KEY", "CHECK", "UNIQUE", "INDEX")):
                        continue

                    parts = line.split()
                    if len(parts) >= 1:
                        col_name = re.sub(r"[\"\`\[\]]", "", parts[0]).strip().lower()
                        col_type = parts[1].upper() if len(parts) > 1 else "TEXT"
                        # Clean up data type (e.g. VARCHAR(255) -> VARCHAR(255))
                        col_type = re.sub(r"[,;]", "", col_type)
                        
                        cols.append({
                            "column_name": col_name,
                            "data_type": col_type,
                            "business_meaning": col_name.replace("_", " ").title(),
                            "is_sensitive": any(k in col_name for k in ["password", "token", "ssn", "secret", "hash", "pin"])
                        })

                if cols:
                    tables.append({
                        "table_name": tbl_name,
                        "business_name": tbl_name.replace("_", " ").title(),
                        "description": f"Table storing {tbl_name.replace('_', ' ')} records",
                        "columns": cols
                    })
        else:
            # Fallback: simple line-by-line format: table_name(col1, col2, col3)
            fallback_pattern = re.compile(r"(\w+)\s*\((.*?)\)", re.DOTALL)
            for m in fallback_pattern.finditer(text):
                tbl_name = m.group(1).strip().lower()
                col_names = [c.strip().split()[0] for c in m.group(2).split(",") if c.strip()]
                cols = [
                    {
                        "column_name": col.strip().lower(),
                        "data_type": "TEXT",
                        "business_meaning": col.replace("_", " ").title(),
                        "is_sensitive": any(k in col.lower() for k in ["password", "token", "ssn", "secret", "hash", "pin"])
                    }
                    for col in col_names if col.strip()
                ]
                if cols:
                    tables.append({
                        "table_name": tbl_name,
                        "business_name": tbl_name.replace("_", " ").title(),
                        "description": f"Table storing {tbl_name.replace('_', ' ')} records",
                        "columns": cols
                    })

        return tables

    @classmethod
    def _parse_prisma(cls, text: str) -> List[Dict[str, Any]]:
        tables = []
        model_pattern = re.compile(r"model\s+(\w+)\s*\{(.*?)\}", re.DOTALL)
        for match in model_pattern.finditer(text):
            tbl_name = match.group(1).strip().lower()
            body = match.group(2).strip()
            cols = []
            for line in body.splitlines():
                line = line.strip()
                if not line or line.startswith("//") or line.startswith("@@"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    col_name = parts[0].strip()
                    col_type = parts[1].strip()
                    cols.append({
                        "column_name": col_name.lower(),
                        "data_type": col_type,
                        "business_meaning": col_name.replace("_", " ").title(),
                        "is_sensitive": any(k in col_name.lower() for k in ["password", "token", "ssn", "secret", "hash", "pin"])
                    })
            if cols:
                tables.append({
                    "table_name": tbl_name,
                    "business_name": tbl_name.replace("_", " ").title(),
                    "description": f"Prisma entity for {tbl_name}",
                    "columns": cols
                })
        return tables

    @classmethod
    def _parse_json(cls, data: Any) -> List[Dict[str, Any]]:
        tables = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "table_name" in item:
                    tables.append(item)
        elif isinstance(data, dict):
            if "tables" in data and isinstance(data["tables"], list):
                tables = data["tables"]
            else:
                for k, v in data.items():
                    if isinstance(v, list):
                        cols = [{"column_name": str(c).lower(), "data_type": "TEXT", "business_meaning": str(c).title()} for c in v]
                        tables.append({"table_name": k.lower(), "business_name": k.title(), "columns": cols})
        return tables

    @classmethod
    def _split_sql_column_lines(cls, body: str) -> List[str]:
        lines = []
        current = []
        paren_depth = 0
        for char in body:
            if char == "(":
                paren_depth += 1
            elif char == ")":
                paren_depth -= 1
            elif char == "," and paren_depth == 0:
                lines.append("".join(current).strip())
                current = []
                continue
            current.append(char)
        if current:
            lines.append("".join(current).strip())
        return lines
