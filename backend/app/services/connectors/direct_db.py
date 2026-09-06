"""
DirectDBExecutor - Connects directly to a client's database.
Supports PostgreSQL, MySQL, and MongoDB.
No middleware, no connector endpoints.
The client just provides a read-only database URL.
"""

import asyncio
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Internal platform tables that must NEVER be discovered or exposed to operational agents
SYSTEM_BLACKLIST_TABLES = {
    "alembic_version", "tenants", "users", "agents", "connections",
    "semantic_tables", "semantic_columns", "rag_sources", "rag_chunks",
    "chat_sessions", "chat_messages", "query_logs", "action_definitions"
}


def normalize_db_url(db_url: str) -> Tuple[str, str]:
    """
    Normalizes dialect-specific database URLs into driver-compatible DSNs.
    Handles SQLAlchemy formats like postgresql+asyncpg://, postgresql+psycopg2://,
    mysql+pymysql://, etc.
    Returns (normalized_url, db_type).
    """
    raw = db_url.strip()
    lower = raw.lower()

    if raw.startswith("gAAAAAB"):
        raise ValueError(
            "Database connection URL is an encrypted token that could not be decrypted. "
            "Please re-enter your database credentials in Agent Studio."
        )
    elif lower.startswith("mongodb://") or lower.startswith("mongodb+srv://"):
        return raw, "mongodb"
    elif lower.startswith("mysql") or lower.startswith("mariadb"):
        # Normalize mysql+pymysql:// or mysql+aiomysql:// -> mysql://
        clean = re.sub(r"^(mysql|mariadb)(\+[a-zA-Z0-9_-]+)?://", "mysql://", raw, flags=re.IGNORECASE)
        return clean, "mysql"
    elif lower.startswith("postgres") or lower.startswith("postgresql"):
        # Normalize postgresql+asyncpg://, postgresql+psycopg2:// -> postgresql://
        clean = re.sub(r"^(postgres|postgresql)(\+[a-zA-Z0-9_-]+)?://", "postgresql://", raw, flags=re.IGNORECASE)
        return clean, "postgresql"
    else:
        raise ValueError(
            f"Unsupported database URL scheme '{raw.split('://')[0] if '://' in raw else raw}'. "
            f"Supported: PostgreSQL (postgresql://, postgresql+asyncpg://), MySQL (mysql://), MongoDB (mongodb://, mongodb+srv://)"
        )


def detect_db_type(db_url: str) -> str:
    """Auto-detect database type from URL scheme."""
    _, db_type = normalize_db_url(db_url)
    return db_type


# ══════════════════════════════════════════════════════════════
#  PostgreSQL Executor (asyncpg)
# ══════════════════════════════════════════════════════════════

_pg_pool_cache: Dict[str, Any] = {}


async def _get_pg_pool(db_url: str):
    import asyncpg

    clean_url, _ = normalize_db_url(db_url)
    base_url = clean_url.split("?")[0]
    ssl_mode = "require" if ("ssl=require" in db_url.lower() or "sslmode=require" in db_url.lower()) else None

    cache_key = f"{base_url}?ssl={ssl_mode}"
    if cache_key in _pg_pool_cache:
        pool = _pg_pool_cache[cache_key]
        try:
            async with pool.acquire(timeout=3) as conn:
                await conn.fetchval("SELECT 1")
            return pool
        except Exception:
            try:
                await pool.close()
            except Exception:
                pass
            del _pg_pool_cache[cache_key]

    pool = await asyncpg.create_pool(base_url, min_size=1, max_size=3, command_timeout=10, timeout=6.0, ssl=ssl_mode)
    _pg_pool_cache[cache_key] = pool
    return pool


class PostgresExecutor:
    @staticmethod
    async def test_connection(db_url: str) -> Dict[str, Any]:
        try:
            pool = await _get_pg_pool(db_url)
            async with pool.acquire(timeout=5) as conn:
                rows = await conn.fetch("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                tables = [r["table_name"] for r in rows if r["table_name"].lower() not in SYSTEM_BLACKLIST_TABLES]
                return {"status": "success", "message": f"Connected! Found {len(tables)} tables.", "tables": tables, "db_type": "postgresql"}
        except Exception as e:
            return {"status": "error", "message": f"Connection failed: {type(e).__name__}: {e}", "tables": []}

    @staticmethod
    async def discover_schema(db_url: str, table_names: List[str]) -> List[Dict[str, Any]]:
        pool = await _get_pg_pool(db_url)
        schemas = []
        async with pool.acquire(timeout=5) as conn:
            for table in table_names:
                rows = await conn.fetch("""
                    SELECT column_name, data_type FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = $1
                    ORDER BY ordinal_position
                """, table)
                columns = [{"column_name": r["column_name"], "data_type": r["data_type"].upper(),
                            "business_meaning": r["column_name"].replace("_", " ").title(),
                            "is_sensitive": any(kw in r["column_name"].lower() for kw in ["password", "secret", "token", "hash", "ssn"])}
                           for r in rows]
                schemas.append({"table_name": table, "business_name": table.replace("_", " ").title(),
                                "description": f"Data from the {table} table", "columns": columns})
        return schemas

    @staticmethod
    async def execute_readonly(db_url: str, sql: str, params: Optional[Dict[str, Any]] = None, max_rows: int = 100) -> List[Dict[str, Any]]:
        _validate_sql_safety(sql)
        pool = await _get_pg_pool(db_url)
        
        # Translate named parameters (:name) into asyncpg positional parameters ($1, $2)
        ordered_values = []
        if params:
            import re
            def _replace_pg_param(match):
                key = match.group(1)
                if key in params:
                    ordered_values.append(params[key])
                    return "$" + str(len(ordered_values))
                return match.group(0)

            sql = re.sub(r":([a-zA-Z0-9_]+)", _replace_pg_param, sql)

        async with pool.acquire(timeout=10) as conn:
            if ordered_values:
                rows = await conn.fetch(sql, *ordered_values)
            else:
                rows = await conn.fetch(sql)
            return [dict(row) for row in rows[:max_rows]]


# ══════════════════════════════════════════════════════════════
#  MySQL Executor (aiomysql)
# ══════════════════════════════════════════════════════════════

_mysql_pool_cache: Dict[str, Any] = {}


def _parse_mysql_url(db_url: str) -> dict:
    """Parse mysql://user:pass@host:port/dbname into connection kwargs."""
    parsed = urlparse(db_url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 3306,
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "db": (parsed.path or "/").lstrip("/"),
    }


async def _get_mysql_pool(db_url: str):
    import aiomysql

    if db_url in _mysql_pool_cache:
        pool = _mysql_pool_cache[db_url]
        if not pool._closed:
            return pool
        del _mysql_pool_cache[db_url]

    params = _parse_mysql_url(db_url)
    pool = await aiomysql.create_pool(minsize=1, maxsize=3, connect_timeout=3, **params)
    _mysql_pool_cache[db_url] = pool
    return pool


class MySQLExecutor:
    @staticmethod
    async def test_connection(db_url: str) -> Dict[str, Any]:
        try:
            pool = await _get_mysql_pool(db_url)
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    params = _parse_mysql_url(db_url)
                    await cur.execute(
                        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME",
                        (params["db"],)
                    )
                    rows = await cur.fetchall()
                    tables = [r[0] for r in rows if r[0].lower() not in SYSTEM_BLACKLIST_TABLES]
                    return {"status": "success", "message": f"Connected! Found {len(tables)} tables.", "tables": tables, "db_type": "mysql"}
        except Exception as e:
            return {"status": "error", "message": f"Connection failed: {type(e).__name__}: {e}", "tables": []}

    @staticmethod
    async def discover_schema(db_url: str, table_names: List[str]) -> List[Dict[str, Any]]:
        pool = await _get_mysql_pool(db_url)
        schemas = []
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                params = _parse_mysql_url(db_url)
                for table in table_names:
                    await cur.execute(
                        "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s ORDER BY ORDINAL_POSITION",
                        (params["db"], table)
                    )
                    rows = await cur.fetchall()
                    columns = [{"column_name": r[0], "data_type": r[1].upper(),
                                "business_meaning": r[0].replace("_", " ").title(),
                                "is_sensitive": any(kw in r[0].lower() for kw in ["password", "secret", "token", "hash", "ssn"])}
                               for r in rows]
                    schemas.append({"table_name": table, "business_name": table.replace("_", " ").title(),
                                    "description": f"Data from the {table} table", "columns": columns})
        return schemas

    @staticmethod
    async def execute_readonly(db_url: str, sql: str, params: Optional[Dict[str, Any]] = None, max_rows: int = 100) -> List[Dict[str, Any]]:
        _validate_sql_safety(sql)
        pool = await _get_mysql_pool(db_url)

        # Translate named parameters (:name) into MySQL positional parameters (%s)
        ordered_values = []
        if params:
            import re
            def _replace_mysql_param(match):
                key = match.group(1)
                if key in params:
                    ordered_values.append(params[key])
                    return "%s"
                return match.group(0)

            sql = re.sub(r":([a-zA-Z0-9_]+)", _replace_mysql_param, sql)

        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                if ordered_values:
                    await cur.execute(sql, tuple(ordered_values))
                else:
                    await cur.execute(sql)
                rows = await cur.fetchmany(max_rows)
                if not rows:
                    return []
                col_names = [desc[0] for desc in cur.description]
                return [dict(zip(col_names, row)) for row in rows]


# ══════════════════════════════════════════════════════════════
#  MongoDB Executor (motor)
# ══════════════════════════════════════════════════════════════

_mongo_client_cache: Dict[str, Any] = {}


async def _get_mongo_client(db_url: str):
    import motor.motor_asyncio

    if db_url in _mongo_client_cache:
        client = _mongo_client_cache[db_url]
        try:
            await client.admin.command("ping")
            return client
        except Exception:
            try:
                client.close()
            except Exception:
                pass
            del _mongo_client_cache[db_url]

    client = motor.motor_asyncio.AsyncIOMotorClient(db_url, serverSelectionTimeoutMS=5000, maxPoolSize=3)
    await client.admin.command("ping")
    _mongo_client_cache[db_url] = client
    return client


async def _locate_mongo_collection(client, db_url: str, collection_name: str):
    """
    Finds and returns the collection object from the specified DB in URL
    or locates it across all user databases in the cluster.
    """
    parsed = urlparse(db_url.split("?")[0])
    db_name = (parsed.path or "/").lstrip("/")

    # If database is specified in URL, use it directly
    if db_name:
        return client[db_name][collection_name]

    # Otherwise search across all accessible user databases in cluster
    try:
        db_names = await client.list_database_names()
        user_dbs = [d for d in db_names if d not in ("admin", "local", "config")]
        for d in user_dbs:
            colls = await client[d].list_collection_names()
            if collection_name in colls:
                return client[d][collection_name]
        if user_dbs:
            return client[user_dbs[0]][collection_name]
    except Exception:
        pass

    return client["test"][collection_name]


def _sanitize_mongo_value(val: Any) -> Any:
    """Recursively converts ObjectIds, datetimes, and Decimals to JSON-serializable types."""
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, list):
        return [_sanitize_mongo_value(item) for item in val]
    if isinstance(val, dict):
        return {str(k): _sanitize_mongo_value(v) for k, v in val.items()}
    return str(val)


class MongoDBExecutor:
    @staticmethod
    async def test_connection(db_url: str) -> Dict[str, Any]:
        try:
            client = await _get_mongo_client(db_url)
            parsed = urlparse(db_url.split("?")[0])
            db_name = (parsed.path or "/").lstrip("/")

            # 1. If explicit database specified in URL path
            if db_name:
                db = client[db_name]
                collections = await db.list_collection_names()
                collections = sorted([c for c in collections if not c.startswith("system.") and c.lower() not in SYSTEM_BLACKLIST_TABLES])
                return {
                    "status": "success",
                    "message": f"Connected! Found {len(collections)} collection(s) in database '{db_name}'.",
                    "tables": collections,
                    "db_type": "mongodb"
                }

            # 2. If no database specified in URL path, discover across all user databases in cluster
            all_collections = []
            db_names = await client.list_database_names()
            user_dbs = [d for d in db_names if d not in ("admin", "local", "config")]
            db_count = len(user_dbs)

            for d in user_dbs:
                colls = await client[d].list_collection_names()
                user_colls = [c for c in colls if not c.startswith("system.") and c.lower() not in SYSTEM_BLACKLIST_TABLES]
                all_collections.extend(user_colls)

            all_collections = sorted(list(set(all_collections)))
            return {
                "status": "success",
                "message": f"Connected to cluster! Found {len(all_collections)} collection(s) across {db_count} database(s).",
                "tables": all_collections,
                "db_type": "mongodb"
            }
        except Exception as e:
            return {"status": "error", "message": f"Connection failed: {type(e).__name__}: {e}", "tables": []}

    @staticmethod
    async def discover_schema(db_url: str, collection_names: List[str]) -> List[Dict[str, Any]]:
        """
        MongoDB doesn't have a fixed schema, so we sample documents
        to infer the field names and types.
        """
        client = await _get_mongo_client(db_url)
        schemas = []

        for coll_name in collection_names:
            collection = await _locate_mongo_collection(client, db_url, coll_name)
            # Sample up to 20 documents to infer schema
            sample_docs = await collection.find().limit(20).to_list(length=20)

            # Merge all keys from sampled documents
            all_keys: Dict[str, str] = {}
            for doc in sample_docs:
                for key, value in doc.items():
                    if key == "_id":
                        continue  # Skip internal MongoDB id
                    if key not in all_keys:
                        all_keys[key] = type(value).__name__.upper()

            columns = [{"column_name": k, "data_type": v,
                         "business_meaning": k.replace("_", " ").replace(".", " ").title(),
                         "is_sensitive": any(kw in k.lower() for kw in ["password", "secret", "token", "hash", "ssn"])}
                        for k, v in all_keys.items()]

            doc_count = await collection.estimated_document_count()
            schemas.append({
                "table_name": coll_name,
                "business_name": coll_name.replace("_", " ").title(),
                "description": f"Collection '{coll_name}' with ~{doc_count} documents in '{collection.database.name}'",
                "columns": columns
            })

        return schemas

    @staticmethod
    async def execute_query(db_url: str, collection_name: str, pipeline: Any, max_rows: int = 100) -> List[Dict[str, Any]]:
        """
        Execute a MongoDB aggregation pipeline against a collection.
        Returns documents as a list of dicts.
        """
        client = await _get_mongo_client(db_url)
        collection = await _locate_mongo_collection(client, db_url, collection_name)

        # Normalize pipeline
        if isinstance(pipeline, dict):
            if any(k.startswith("$") for k in pipeline.keys()):
                pipeline = [pipeline]
            else:
                pipeline = [{"$match": pipeline}]
        elif not isinstance(pipeline, list):
            pipeline = []

        # Safety: Add $limit if not present
        has_limit = any("$limit" in stage for stage in pipeline if isinstance(stage, dict))
        if not has_limit:
            pipeline.append({"$limit": max_rows})

        cursor = collection.aggregate(pipeline)
        results = await cursor.to_list(length=max_rows)

        # Deep sanitize for JSON safety
        clean_results = []
        for doc in results:
            clean_results.append(_sanitize_mongo_value(doc))

        return clean_results


# ══════════════════════════════════════════════════════════════
#  Unified Interface (auto-detects DB type)
# ══════════════════════════════════════════════════════════════

def _validate_sql_safety(sql: str):
    """Block dangerous SQL operations."""
    normalized = sql.strip().upper()
    if not normalized.startswith("SELECT"):
        raise ValueError(f"Only SELECT queries are allowed. Got: {normalized[:20]}")
    blocked = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE", "GRANT", "REVOKE"]
    for kw in blocked:
        if kw in normalized:
            raise ValueError(f"Blocked dangerous SQL keyword: {kw}")


class DirectDBExecutor:
    """
    Unified interface that auto-detects the database type from the URL
    and delegates to the appropriate executor.
    """

    @staticmethod
    def _get_executor(db_url: str):
        db_type = detect_db_type(db_url)
        if db_type == "postgresql":
            return PostgresExecutor, db_type
        elif db_type == "mysql":
            return MySQLExecutor, db_type
        elif db_type == "mongodb":
            return MongoDBExecutor, db_type
        raise ValueError(f"Unsupported database type: {db_type}")

    @staticmethod
    async def test_connection(db_url: str) -> Dict[str, Any]:
        try:
            executor, _ = DirectDBExecutor._get_executor(db_url)
            return await asyncio.wait_for(executor.test_connection(db_url), timeout=7.0)
        except (ValueError, asyncio.TimeoutError) as e:
            msg = "Connection timed out (Host unreachable or waking up from sleep)" if isinstance(e, asyncio.TimeoutError) else str(e)
            return {"status": "error", "message": msg, "tables": []}
        except Exception as e:
            return {"status": "error", "message": str(e), "tables": []}

    @staticmethod
    async def discover_schema(db_url: str, table_names: List[str]) -> List[Dict[str, Any]]:
        try:
            executor, _ = DirectDBExecutor._get_executor(db_url)
            return await asyncio.wait_for(executor.discover_schema(db_url, table_names), timeout=8.0)
        except Exception as e:
            logger.error(f"Error discovering schema: {e}")
            return []

    @staticmethod
    async def execute_readonly(db_url: str, sql: str, params: Optional[Dict[str, Any]] = None, max_rows: int = 100) -> List[Dict[str, Any]]:
        """For SQL databases (PostgreSQL, MySQL). Runs a validated SELECT query."""
        executor, db_type = DirectDBExecutor._get_executor(db_url)
        if db_type == "mongodb":
            raise ValueError("Use execute_mongo_query() for MongoDB connections.")
        return await executor.execute_readonly(db_url, sql, params, max_rows)

    @staticmethod
    async def execute_mongo_query(db_url: str, collection_name: str, pipeline: list, max_rows: int = 100) -> List[Dict[str, Any]]:
        """For MongoDB. Runs an aggregation pipeline against a collection."""
        return await MongoDBExecutor.execute_query(db_url, collection_name, pipeline, max_rows)

    @staticmethod
    async def close_all_pools():
        """Close all cached connection pools. Call on app shutdown."""
        for _, pool in _pg_pool_cache.items():
            try:
                await pool.close()
            except Exception:
                pass
        _pg_pool_cache.clear()

        for _, pool in _mysql_pool_cache.items():
            try:
                pool.close()
                await pool.wait_closed()
            except Exception:
                pass
        _mysql_pool_cache.clear()

        for _, client in _mongo_client_cache.items():
            try:
                client.close()
            except Exception:
                pass
        _mongo_client_cache.clear()
