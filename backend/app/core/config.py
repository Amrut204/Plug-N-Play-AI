from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import os
import secrets
import logging

logger = logging.getLogger("app.core.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True, 
        env_file=(".env", "backend/.env", "../.env"), 
        extra="ignore"
    )

    PROJECT_NAME: str = "Plug-N-Play AI Data Layer"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "enterprise_super_secret_pnp_jwt_key_32_bytes_long_change_in_prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    SESSION_TOKEN_EXPIRE_MINUTES: int = 15      # Short-lived widget session

    # Rate Limiting & Upload Guardrails
    CHAT_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("CHAT_RATE_LIMIT_PER_MINUTE", "60"))
    MAX_UPLOAD_SIZE_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(25 * 1024 * 1024)))  # 25 MB
    ENABLE_LOCAL_EMBEDDINGS: bool = os.getenv("ENABLE_LOCAL_EMBEDDINGS", "true").lower() == "true"
    
    # Database
    # Default to sqlite+aiosqlite for local testing/dev if Postgres is not running
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite+aiosqlite:///./plug_n_play_platform.db"
    )
    
    # Redis
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", None)
    
    # LLM Providers
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", None)
    GROQ_API_KEY_1: Optional[str] = os.getenv("GROQ_API_KEY_1", None)
    GROQ_API_KEY_2: Optional[str] = os.getenv("GROQ_API_KEY_2", None)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY", None)

    @property
    def groq_api_keys(self) -> List[str]:
        """Returns all configured Groq API keys in priority order without duplicates."""
        keys = []
        for k in [self.GROQ_API_KEY, self.GROQ_API_KEY_1, self.GROQ_API_KEY_2]:
            if k and k.strip() and k.strip() not in keys:
                keys.append(k.strip())
        return keys
    
    # Smart default: If any Groq key is present and OpenAI is not, default to Groq
    DEFAULT_MODEL_PROVIDER: str = "groq" if (os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_1") or os.getenv("GROQ_API_KEY_2")) and not os.getenv("OPENAI_API_KEY") else "openai"
    DEFAULT_MODEL_NAME: str = "qwen/qwen3.8-27b" if (os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_1") or os.getenv("GROQ_API_KEY_2")) and not os.getenv("OPENAI_API_KEY") else "gpt-4o-mini"
    
    # Email / SMTP Configuration
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER", None)
    SMTP_PASS: Optional[str] = os.getenv("SMTP_PASS", None)
    SMTP_FROM: Optional[str] = os.getenv("SMTP_FROM", None)

    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "629754361477-2sitaqfnnqs4n5qi8v0ivt2cnbeirg6e.apps.googleusercontent.com")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET", "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")

    # CORS Configuration
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ORIGINS or self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Connector Protocol
    CONNECTOR_TIMEOUT_SECONDS: float = 10.0
    CONNECTOR_MAX_ROWS: int = 50


settings = Settings()

# Production Security Safeguard
if settings.ENVIRONMENT == "production" and settings.SECRET_KEY == "enterprise_super_secret_pnp_jwt_key_32_bytes_long_change_in_prod":
    settings.SECRET_KEY = secrets.token_hex(32)
    logger.warning(
        "⚠️ [SECURITY WARNING] Default insecure SECRET_KEY detected in production! "
        "Generated an ephemeral 256-bit cryptographically secure key for this session. "
        "Please configure SECRET_KEY in your Render environment variables."
    )
