import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# URL Normalization for Cloud Databases (Neon, Supabase, Render Postgres)
def normalize_database_url(url: str) -> str:
    if not url:
        return "sqlite+aiosqlite:///./plug_n_play_platform.db"
    clean = url.strip()
    if clean.startswith("postgres://"):
        clean = "postgresql+asyncpg://" + clean[len("postgres://"):]
    elif clean.startswith("postgresql://") and not clean.startswith("postgresql+asyncpg://"):
        clean = "postgresql+asyncpg://" + clean[len("postgresql://"):]
    if "sslmode=require" in clean:
        clean = clean.replace("sslmode=require", "ssl=require")
    return clean

# Detect test environment
is_testing = "pytest" in sys.modules or os.getenv("TESTING", "false").lower() == "true"
active_db_url = "sqlite+aiosqlite:///:memory:" if is_testing else normalize_database_url(settings.DATABASE_URL)

connect_args = {}
engine_kwargs = {"echo": False, "future": True}

if "sqlite" in active_db_url:
    connect_args["check_same_thread"] = False
    engine_kwargs["connect_args"] = connect_args
elif "postgres" in active_db_url:
    # Disable statement caching for PgBouncer / Neon transaction poolers
    connect_args["statement_cache_size"] = 0
    engine_kwargs["connect_args"] = connect_args
    # Connection pooling with pre-ping and keepalives for cloud databases (Neon, Supabase)
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

engine = create_async_engine(
    active_db_url,
    **engine_kwargs
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


async def get_db():
    """Async database session dependency."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables and run migration statements."""
    # Ensure all ORM models are registered with Base.metadata
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        # Create all tables first
        await conn.run_sync(Base.metadata.create_all)

        # If postgres, try creating vector extension and applying column migrations
        if "postgres" in active_db_url:
            try:
                from sqlalchemy import text
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            except Exception as e:
                logger.warning(f"Could not enable pgvector extension: {e}")

            alter_statements = [
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS guardrail_config TEXT;",
                "ALTER TABLE agents ADD COLUMN IF NOT EXISTS allowed_domains VARCHAR(500);",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(50) DEFAULT 'free';",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS billing_cycle VARCHAR(20) DEFAULT 'monthly';",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS monthly_query_limit INTEGER DEFAULT 150;",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS queries_used_this_month INTEGER DEFAULT 0;",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS billing_currency VARCHAR(10) DEFAULT 'USD';",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(100);",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(100);",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(50) DEFAULT 'active';",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS subscription_period_end TIMESTAMPTZ;",
                "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS is_escalated BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS escalation_reason TEXT;",
                "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS escalation_contact VARCHAR(255);",
                "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS is_resolved BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS email VARCHAR(255);",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS full_name VARCHAR(255);",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500);",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS otp_code VARCHAR(10);",
                "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS otp_expires_at TIMESTAMPTZ;"
            ]
            for stmt_str in alter_statements:
                try:
                    from sqlalchemy import text
                    await conn.execute(text(stmt_str))
                except Exception as col_err:
                    logger.debug(f"Column migration notice: {col_err}")
