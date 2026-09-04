import sqlite3
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ColumnSchema:
    column_name: str
    data_type: str
    business_meaning: str
    allowed_operations: List[str] = None
    is_sensitive: bool = False
    row_identity_binding: Optional[str] = None

    def __post_init__(self):
        if self.allowed_operations is None:
            self.allowed_operations = ["SELECT", "WHERE", "JOIN"]


@dataclass
class TableSchema:
    table_name: str
    business_name: str
    description: str
    columns: List[ColumnSchema]
    allowed_roles: List[str] = None

    def __post_init__(self):
        if self.allowed_roles is None:
            self.allowed_roles = ["admin", "user", "student", "faculty"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "business_name": self.business_name,
            "description": self.description,
            "allowed_roles": self.allowed_roles,
            "columns": [asdict(c) for c in self.columns]
        }


class BaseExecutor:
    def execute_query(self, sql: str, params: Dict[str, Any], max_rows: int = 50) -> List[Dict[str, Any]]:
        raise NotImplementedError


class SQLiteExecutor(BaseExecutor):
    """Safe SQLite read-only executor."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def execute_query(self, sql: str, params: Dict[str, Any], max_rows: int = 50) -> List[Dict[str, Any]]:
        # Connect in read-only mode using sqlite URI
        uri = f"file:{self.db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute(sql, params)
            rows = cursor.fetchmany(max_rows)
            return [dict(row) for row in rows]
        finally:
            cursor.close()
            conn.close()
