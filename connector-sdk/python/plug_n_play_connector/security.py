import hmac
import hashlib
import time
from typing import Tuple


def verify_hmac_signature(
    secret: str,
    timestamp: str,
    body: bytes,
    received_signature: str,
    max_drift_seconds: int = 300
) -> Tuple[bool, str]:
    """
    Validates HMAC-SHA256 signature and checks timestamp freshness to protect against replay attacks.
    """
    try:
        ts = int(timestamp)
        now = int(time.time())
        if abs(now - ts) > max_drift_seconds:
            return False, "Timestamp expired or clock drift exceeded limit."
    except (ValueError, TypeError):
        return False, "Invalid timestamp format."

    body_hash = hashlib.sha256(body).hexdigest()
    message = f"{timestamp}.{body_hash}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, received_signature):
        return False, "Invalid signature."

    return True, "Valid"
