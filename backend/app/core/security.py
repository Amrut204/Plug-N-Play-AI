import hmac
import hashlib
import time
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
from jose import jwt, JWTError
from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against an existing bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generate a high-security bcrypt password hash."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def generate_api_key(prefix: str = "pnp") -> str:
    """Generate a high-entropy secure API key."""
    random_bytes = secrets.token_hex(24)
    return f"{prefix}_{random_bytes}"


def hash_api_key(api_key: str) -> str:
    """Compute SHA256 hash of an API key for safe database storage."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create signed JWT for administrative users or tenant service accounts."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_widget_session_token(
    tenant_id: str,
    agent_id: str,
    external_user_id: str,
    user_role: str = "user",
    metadata: Optional[Dict[str, Any]] = None,
    expires_minutes: int = 15
) -> str:
    """
    Create a short-lived signed JWT session token for the embeddable widget.
    Clients generate this via their backend after authenticating their user.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)
    payload = {
        "sub": external_user_id,
        "tenant_id": str(tenant_id),
        "agent_id": str(agent_id),
        "role": user_role,
        "meta": metadata or {},
        "exp": expire,
        "iat": now,
        "type": "widget_session"
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_session_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a signed JWT session token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


# --- Connector Mutual HMAC Authentication ---

def generate_connector_signature(secret: str, timestamp: str, body: bytes) -> str:
    """
    Generate HMAC-SHA256 signature for mutual authentication between
    Plug-N-Play Cloud and the Client Connector.
    Signature = HMAC-SHA256(secret, timestamp + "." + sha256(body))
    """
    body_hash = hashlib.sha256(body).hexdigest()
    message = f"{timestamp}.{body_hash}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_connector_signature(
    secret: str, 
    timestamp: str, 
    body: bytes, 
    received_signature: str,
    max_age_seconds: int = 300
) -> bool:
    """
    Verify timestamp freshness (prevent replay attacks) and validate HMAC signature.
    """
    try:
        ts = int(timestamp)
        now = int(time.time())
        if abs(now - ts) > max_age_seconds:
            return False
    except ValueError:
        return False
        
    expected_sig = generate_connector_signature(secret, timestamp, body)
    return hmac.compare_digest(expected_sig, received_signature)
