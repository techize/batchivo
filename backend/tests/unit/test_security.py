"""Unit tests for JWT security utilities (admin user tokens)."""

import uuid
from datetime import timedelta

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
)

USER_ID = str(uuid.uuid4())
TENANT_ID = str(uuid.uuid4())
EMAIL = "admin@batchivo.com"


def make_payload(**overrides) -> dict:
    return {"user_id": USER_ID, "email": EMAIL, "tenant_id": TENANT_ID, **overrides}


class TestCreateAccessToken:
    """Tests for create_access_token."""

    def test_returns_non_empty_string(self):
        token = create_access_token(make_payload())
        assert isinstance(token, str) and len(token) > 0

    def test_token_is_decodeable(self):
        token = create_access_token(make_payload())
        assert decode_token(token) is not None

    def test_token_contains_user_id(self):
        token = create_access_token(make_payload())
        data = decode_token(token)
        assert str(data.user_id) == USER_ID

    def test_token_contains_email(self):
        token = create_access_token(make_payload())
        data = decode_token(token)
        assert data.email == EMAIL

    def test_token_contains_tenant_id(self):
        token = create_access_token(make_payload())
        data = decode_token(token)
        assert str(data.tenant_id) == TENANT_ID

    def test_tenant_id_optional(self):
        token = create_access_token({"user_id": USER_ID, "email": EMAIL})
        data = decode_token(token)
        assert data.tenant_id is None

    def test_token_type_is_access(self):
        token = create_access_token(make_payload())
        assert verify_token_type(token, "access") is True

    def test_token_type_is_not_refresh(self):
        token = create_access_token(make_payload())
        assert verify_token_type(token, "refresh") is False

    def test_custom_expires_delta_accepted(self):
        token = create_access_token(make_payload(), expires_delta=timedelta(minutes=5))
        assert decode_token(token) is not None

    def test_platform_admin_flag_preserved(self):
        token = create_access_token(make_payload(is_platform_admin=True))
        data = decode_token(token)
        assert data.is_platform_admin is True

    def test_platform_admin_defaults_false(self):
        token = create_access_token(make_payload())
        data = decode_token(token)
        assert data.is_platform_admin is False


class TestCreateRefreshToken:
    """Tests for create_refresh_token."""

    def test_returns_non_empty_string(self):
        token = create_refresh_token(make_payload())
        assert isinstance(token, str) and len(token) > 0

    def test_token_is_decodeable(self):
        token = create_refresh_token(make_payload())
        assert decode_token(token) is not None

    def test_token_type_is_refresh(self):
        token = create_refresh_token(make_payload())
        assert verify_token_type(token, "refresh") is True

    def test_token_type_is_not_access(self):
        token = create_refresh_token(make_payload())
        assert verify_token_type(token, "access") is False

    def test_access_and_refresh_are_different(self):
        access = create_access_token(make_payload())
        refresh = create_refresh_token(make_payload())
        assert access != refresh


class TestDecodeToken:
    """Tests for decode_token."""

    def test_valid_token_decoded(self):
        token = create_access_token(make_payload())
        data = decode_token(token)
        assert data is not None

    def test_invalid_token_returns_none(self):
        assert decode_token("not-a-jwt") is None

    def test_empty_string_returns_none(self):
        assert decode_token("") is None

    def test_missing_user_id_returns_none(self):
        # Token with no user_id should return None
        token = create_access_token({"email": EMAIL})
        assert decode_token(token) is None

    def test_missing_email_returns_none(self):
        token = create_access_token({"user_id": USER_ID})
        assert decode_token(token) is None


class TestVerifyTokenType:
    """Tests for verify_token_type."""

    def test_access_token_matches_access(self):
        token = create_access_token(make_payload())
        assert verify_token_type(token, "access") is True

    def test_refresh_token_matches_refresh(self):
        token = create_refresh_token(make_payload())
        assert verify_token_type(token, "refresh") is True

    def test_access_does_not_match_refresh(self):
        token = create_access_token(make_payload())
        assert verify_token_type(token, "refresh") is False

    def test_invalid_token_returns_false(self):
        assert verify_token_type("garbage", "access") is False

    def test_empty_string_returns_false(self):
        assert verify_token_type("", "access") is False
