"""Unit tests for password hashing utilities."""

from app.auth.password import get_password_hash, verify_password


class TestGetPasswordHash:
    """Tests for get_password_hash."""

    def test_returns_string(self):
        result = get_password_hash("mypassword")
        assert isinstance(result, str)

    def test_hash_differs_from_original(self):
        result = get_password_hash("mypassword")
        assert result != "mypassword"

    def test_hash_starts_with_bcrypt_prefix(self):
        result = get_password_hash("mypassword")
        assert result.startswith("$2b$")

    def test_same_input_produces_different_hashes(self):
        # bcrypt uses random salt, so two hashes of the same password differ
        hash1 = get_password_hash("mypassword")
        hash2 = get_password_hash("mypassword")
        assert hash1 != hash2

    def test_different_passwords_produce_different_hashes(self):
        hash1 = get_password_hash("password1")
        hash2 = get_password_hash("password2")
        assert hash1 != hash2

    def test_long_password(self):
        long_pw = "a" * 72  # bcrypt max effective length
        result = get_password_hash(long_pw)
        assert isinstance(result, str)

    def test_special_characters(self):
        result = get_password_hash("p@$$w0rd!#%&*()")
        assert isinstance(result, str)


class TestVerifyPassword:
    """Tests for verify_password."""

    def test_correct_password_returns_true(self):
        hashed = get_password_hash("correctpassword")
        assert verify_password("correctpassword", hashed) is True

    def test_wrong_password_returns_false(self):
        hashed = get_password_hash("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_empty_password_wrong(self):
        hashed = get_password_hash("somepassword")
        assert verify_password("", hashed) is False

    def test_case_sensitive(self):
        hashed = get_password_hash("Password")
        assert verify_password("password", hashed) is False
        assert verify_password("PASSWORD", hashed) is False
        assert verify_password("Password", hashed) is True

    def test_roundtrip_with_special_chars(self):
        pw = "p@$$w0rd!#%&*()"
        hashed = get_password_hash(pw)
        assert verify_password(pw, hashed) is True

    def test_different_hash_of_same_password_still_verifies(self):
        # Even though hashes differ (random salt), both should verify
        pw = "samepassword"
        hash1 = get_password_hash(pw)
        hash2 = get_password_hash(pw)
        assert verify_password(pw, hash1) is True
        assert verify_password(pw, hash2) is True
