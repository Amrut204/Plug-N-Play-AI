import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet
from app.core.config import settings


def _get_fernet_key() -> bytes:
    """
    Derives a 32-byte urlsafe base64-encoded key from settings.SECRET_KEY.
    """
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return base64.urlsafe_b64encode(digest)


class CryptoService:
    """
    Enterprise Data-at-Rest Encryption Service using Fernet authenticated symmetric encryption.
    Protects connector shared secrets, credentials, and sensitive configuration.
    """
    _fernet: Optional[Fernet] = None

    @classmethod
    def _get_instance(cls) -> Fernet:
        if cls._fernet is None:
            cls._fernet = Fernet(_get_fernet_key())
        return cls._fernet

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """
        Encrypts plaintext string into an authenticated ciphertext string.
        """
        if not plaintext:
            return ""
        cipher = cls._get_instance()
        return cipher.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        """
        Decrypts ciphertext string back into plaintext.
        Falls back to ciphertext if not encrypted (legacy migration support).
        """
        if not ciphertext:
            return ""
        cipher = cls._get_instance()
        try:
            return cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except Exception:
            # Return raw string if already unencrypted
            return ciphertext
