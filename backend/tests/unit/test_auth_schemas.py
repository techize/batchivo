"""
Tests for authentication Pydantic schemas.
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    PasswordResetConfirm,
    PasswordResetRequest,
    Token,
    TokenData,
    TokenRefresh,
    UserLogin,
    UserRegister,
)


class TestUserRegister:
    def test_valid_minimal(self):
        r = UserRegister(email="user@example.com", password="password1")
        assert r.email == "user@example.com"
        assert r.full_name is None
        assert r.tenant_name is None

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            UserRegister(email="not-an-email", password="password1")

    def test_password_too_short_raises(self):
        with pytest.raises(ValidationError):
            UserRegister(email="user@example.com", password="short")

    def test_password_exactly_8_accepted(self):
        r = UserRegister(email="user@example.com", password="12345678")
        assert len(r.password) == 8

    def test_full_name_optional(self):
        r = UserRegister(email="user@example.com", password="password1", full_name="Jane")
        assert r.full_name == "Jane"

    def test_tenant_name_optional(self):
        r = UserRegister(email="user@example.com", password="password1", tenant_name="My Shop")
        assert r.tenant_name == "My Shop"


class TestUserLogin:
    def test_valid(self):
        login = UserLogin(email="user@example.com", password="anypass")
        assert login.email == "user@example.com"

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            UserLogin(email="invalid", password="pass")


class TestToken:
    def test_valid(self):
        t = Token(access_token="abc123", refresh_token="xyz789")
        assert t.token_type == "bearer"

    def test_custom_token_type(self):
        t = Token(access_token="abc", refresh_token="xyz", token_type="JWT")
        assert t.token_type == "JWT"


class TestTokenRefresh:
    def test_valid(self):
        tr = TokenRefresh(refresh_token="refresh-token-value")
        assert tr.refresh_token == "refresh-token-value"

    def test_missing_refresh_token_raises(self):
        with pytest.raises(ValidationError):
            TokenRefresh()


class TestTokenData:
    def test_valid_minimal(self):
        uid = uuid4()
        td = TokenData(user_id=uid, email="user@example.com")
        assert td.tenant_id is None
        assert td.is_platform_admin is False

    def test_platform_admin_flag(self):
        uid = uuid4()
        td = TokenData(user_id=uid, email="admin@example.com", is_platform_admin=True)
        assert td.is_platform_admin is True

    def test_with_tenant_id(self):
        uid = uuid4()
        tid = uuid4()
        td = TokenData(user_id=uid, email="user@example.com", tenant_id=tid)
        assert td.tenant_id == tid


class TestPasswordResetRequest:
    def test_valid_email(self):
        r = PasswordResetRequest(email="user@example.com")
        assert r.email == "user@example.com"

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetRequest(email="not-an-email")


class TestPasswordResetConfirm:
    def test_valid(self):
        r = PasswordResetConfirm(token="reset-token", new_password="newpass1")
        assert r.token == "reset-token"

    def test_new_password_too_short_raises(self):
        with pytest.raises(ValidationError):
            PasswordResetConfirm(token="tok", new_password="short")

    def test_new_password_exactly_8_accepted(self):
        r = PasswordResetConfirm(token="tok", new_password="12345678")
        assert len(r.new_password) == 8
