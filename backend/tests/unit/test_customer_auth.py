"""Unit tests for customer authentication utilities."""

import uuid
from datetime import timedelta

from app.auth.customer_dependencies import (
    create_customer_access_token,
    create_customer_refresh_token,
    decode_customer_token,
    verify_customer_token_type,
)


CUSTOMER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
TENANT_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
EMAIL = "customer@example.com"


class TestCreateCustomerAccessToken:
    """Tests for create_customer_access_token."""

    def test_returns_non_empty_string(self):
        token = create_customer_access_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_is_decodeable(self):
        token = create_customer_access_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        data = decode_customer_token(token)
        assert data is not None

    def test_token_contains_customer_id(self):
        token = create_customer_access_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        data = decode_customer_token(token)
        assert data.customer_id == CUSTOMER_ID

    def test_token_contains_tenant_id(self):
        token = create_customer_access_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        data = decode_customer_token(token)
        assert data.tenant_id == TENANT_ID

    def test_token_contains_email(self):
        token = create_customer_access_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        data = decode_customer_token(token)
        assert data.email == EMAIL

    def test_token_type_is_customer_access(self):
        token = create_customer_access_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        assert verify_customer_token_type(token, "customer_access") is True

    def test_token_type_is_not_refresh(self):
        token = create_customer_access_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        assert verify_customer_token_type(token, "customer_refresh") is False

    def test_custom_expires_delta(self):
        # Should not raise even with very short expiry
        token = create_customer_access_token(
            CUSTOMER_ID, TENANT_ID, EMAIL, expires_delta=timedelta(minutes=5)
        )
        data = decode_customer_token(token)
        assert data is not None


class TestCreateCustomerRefreshToken:
    """Tests for create_customer_refresh_token."""

    def test_returns_non_empty_string(self):
        token = create_customer_refresh_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_is_decodeable(self):
        token = create_customer_refresh_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        data = decode_customer_token(token)
        assert data is not None

    def test_token_contains_correct_fields(self):
        token = create_customer_refresh_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        data = decode_customer_token(token)
        assert data.customer_id == CUSTOMER_ID
        assert data.tenant_id == TENANT_ID
        assert data.email == EMAIL

    def test_token_type_is_customer_refresh(self):
        token = create_customer_refresh_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        assert verify_customer_token_type(token, "customer_refresh") is True

    def test_token_type_is_not_access(self):
        token = create_customer_refresh_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        assert verify_customer_token_type(token, "customer_access") is False

    def test_access_and_refresh_tokens_are_different(self):
        access = create_customer_access_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        refresh = create_customer_refresh_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        assert access != refresh


class TestDecodeCustomerToken:
    """Tests for decode_customer_token."""

    def test_valid_access_token_decoded_correctly(self):
        token = create_customer_access_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        data = decode_customer_token(token)
        assert data is not None
        assert data.customer_id == CUSTOMER_ID

    def test_invalid_token_returns_none(self):
        assert decode_customer_token("not-a-valid-jwt") is None

    def test_empty_string_returns_none(self):
        assert decode_customer_token("") is None

    def test_returns_customer_token_data_type(self):
        from app.auth.customer_dependencies import CustomerTokenData
        token = create_customer_access_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        data = decode_customer_token(token)
        assert isinstance(data, CustomerTokenData)


class TestVerifyCustomerTokenType:
    """Tests for verify_customer_token_type."""

    def test_correct_access_type(self):
        token = create_customer_access_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        assert verify_customer_token_type(token, "customer_access") is True

    def test_wrong_type_returns_false(self):
        token = create_customer_access_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        assert verify_customer_token_type(token, "customer_refresh") is False

    def test_invalid_token_returns_false(self):
        assert verify_customer_token_type("garbage-token", "customer_access") is False

    def test_empty_token_returns_false(self):
        assert verify_customer_token_type("", "customer_access") is False

    def test_correct_refresh_type(self):
        token = create_customer_refresh_token(CUSTOMER_ID, TENANT_ID, EMAIL)
        assert verify_customer_token_type(token, "customer_refresh") is True
