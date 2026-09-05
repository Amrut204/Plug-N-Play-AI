import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet
from app.core.config import settings


class DecryptionError(ValueError):
    """Raised when an encrypted secret fails authentication or decryption."""
    pass


DEFAULT_KEY = "enterprise_super_secret_pnp_jwt_key_32_bytes_long_change_in_prod"


def _derive_fernet_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def _get_fernet_key() -> bytes:
    """
    Derives a 32-byte urlsafe base64-encoded key from settings.SECRET_KEY.
    """
    return _derive_fernet_key(settings.SECRET_KEY)


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
        Attempts primary key first, then known fallback keys.
        Raises DecryptionError if Fernet ciphertext fails all keys.
        """
        if not ciphertext:
            return ""
        
        # Fast path: plaintext that is not Fernet-encrypted
        if not ciphertext.startswith("gAAAAAB"):
            return ciphertext

        # 1. Try primary key
        cipher = cls._get_instance()
        try:
            return cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except Exception:
            pass

        # 2. Try default fallback key if different
        if settings.SECRET_KEY != DEFAULT_KEY:
            try:
                fallback_cipher = Fernet(_derive_fernet_key(DEFAULT_KEY))
                return fallback_cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
            except Exception:
                pass

        # If it clearly is a Fernet ciphertext that failed all available keys, raise DecryptionError
        raise DecryptionError(
            "Encrypted credentials cannot be decrypted with the current or fallback SECRET_KEY. "
            "The database connection must be re-entered in the Agent Studio."
        )

