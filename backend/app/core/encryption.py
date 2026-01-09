"""Encryption utilities for secure credential storage.

Uses Fernet symmetric encryption (AES-128-CBC) for encrypting sensitive data
like API credentials stored in the database.
"""

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


@lru_cache(maxsize=1)
def _get_encryption_key() -> bytes:
    """Derive a Fernet-compatible key from the application secret key.

    Uses SHA-256 to derive a 32-byte key, then base64 encodes it
    for Fernet compatibility.
    """
    settings = get_settings()
    # Use SHA-256 to get a consistent 32-byte key from secret_key
    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    # Fernet requires base64-encoded 32-byte key
    return base64.urlsafe_b64encode(key_bytes)


def _get_fernet() -> Fernet:
    """Get a Fernet instance with the derived key."""
    return Fernet(_get_encryption_key())


def encrypt_value(value: str) -> str:
    """Encrypt a string value.

    Args:
        value: The plaintext string to encrypt

    Returns:
        Base64-encoded encrypted string (Fernet token)
    """
    if not value:
        return ""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(value.encode())
    return encrypted.decode()


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt an encrypted string value.

    Args:
        encrypted_value: The Fernet token to decrypt

    Returns:
        The decrypted plaintext string

    Raises:
        InvalidToken: If the token is invalid or corrupted
    """
    if not encrypted_value:
        return ""
    fernet = _get_fernet()
    decrypted = fernet.decrypt(encrypted_value.encode())
    return decrypted.decode()


def mask_credential(value: str, visible_chars: int = 4) -> str:
    """Mask a credential showing only the last N characters.

    Args:
        value: The credential to mask
        visible_chars: Number of characters to show at the end

    Returns:
        Masked string like "...abc123"
    """
    if not value:
        return ""
    if len(value) <= visible_chars:
        return "*" * len(value)
    return "..." + value[-visible_chars:]


def is_encrypted(value: str) -> bool:
    """Check if a value appears to be a Fernet-encrypted token.

    Args:
        value: The string to check

    Returns:
        True if the value looks like a Fernet token
    """
    if not value:
        return False
    # Fernet tokens start with 'gAAAAA' (base64-encoded version byte + timestamp)
    return value.startswith("gAAAAA")


def safe_decrypt(encrypted_value: str) -> str | None:
    """Safely decrypt a value, returning None on failure.

    Args:
        encrypted_value: The Fernet token to decrypt

    Returns:
        The decrypted string, or None if decryption fails
    """
    if not encrypted_value:
        return None
    try:
        return decrypt_value(encrypted_value)
    except InvalidToken:
        return None
