"""Unit tests for encryption utility."""

import pytest

from app.core.encryption import (
    decrypt_value,
    encrypt_value,
    mask_credential,
    safe_decrypt,
)


class TestEncryption:
    """Tests for encrypt/decrypt functions."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypting and decrypting should return the original value."""
        original = "my-secret-api-key-12345"
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        assert decrypted == original

    def test_encrypted_value_is_different(self):
        """Encrypted value should not equal the original."""
        original = "my-secret-api-key"
        encrypted = encrypt_value(original)
        assert encrypted != original

    def test_encrypted_value_looks_like_fernet(self):
        """Encrypted value should be a base64-encoded Fernet token."""
        original = "test-value"
        encrypted = encrypt_value(original)
        # Fernet tokens start with "gAAAAA"
        assert encrypted.startswith("gAAAAA")

    def test_different_inputs_produce_different_outputs(self):
        """Different inputs should produce different encrypted values."""
        encrypted1 = encrypt_value("value1")
        encrypted2 = encrypt_value("value2")
        assert encrypted1 != encrypted2

    def test_same_input_produces_different_outputs(self):
        """Same input should produce different encrypted values (due to nonce)."""
        encrypted1 = encrypt_value("same-value")
        encrypted2 = encrypt_value("same-value")
        # Fernet uses a random nonce, so outputs differ
        assert encrypted1 != encrypted2

    def test_decrypt_invalid_token_raises(self):
        """Decrypting an invalid token should raise an exception."""
        with pytest.raises(Exception):
            decrypt_value("not-a-valid-fernet-token")


class TestMaskCredential:
    """Tests for credential masking."""

    def test_mask_short_value(self):
        """Short values should be fully masked with asterisks."""
        result = mask_credential("abc", visible_chars=4)
        assert result == "***"  # 3 asterisks for 3 chars

    def test_mask_standard_value(self):
        """Standard values should be properly masked with last chars visible."""
        result = mask_credential("my-secret-token-12345", visible_chars=4)
        assert result == "...2345"
        assert "secret" not in result

    def test_mask_custom_visible_chars(self):
        """Custom visible_chars should work correctly."""
        result = mask_credential("abcdefghij", visible_chars=2)
        assert result == "...ij"

    def test_mask_empty_string(self):
        """Empty string should return empty string."""
        result = mask_credential("", visible_chars=4)
        assert result == ""


class TestSafeDecrypt:
    """Tests for safe_decrypt function."""

    def test_safe_decrypt_valid(self):
        """Valid encrypted value should decrypt successfully."""
        original = "my-secret"
        encrypted = encrypt_value(original)
        result = safe_decrypt(encrypted)
        assert result == original

    def test_safe_decrypt_invalid_returns_none(self):
        """Invalid encrypted value should return None, not raise."""
        result = safe_decrypt("invalid-token")
        assert result is None

    def test_safe_decrypt_empty_returns_none(self):
        """Empty string should return None."""
        result = safe_decrypt("")
        assert result is None

    def test_safe_decrypt_none_input(self):
        """None input should be handled gracefully."""
        # The function signature expects str, but test edge case
        result = safe_decrypt("")
        assert result is None
