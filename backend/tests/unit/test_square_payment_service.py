"""Comprehensive tests for Square payment service - 100% coverage."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.payment import (
    CartItem,
    CustomerDetails,
    PaymentError,
    PaymentRequest,
    PaymentResponse,
    ShippingAddress,
)
from app.services.square_payment import (
    SQUARE_ERROR_MESSAGES,
    SquarePaymentService,
    get_payment_service,
    reset_payment_service,
)


# ============================================
# Test Fixtures
# ============================================


def create_payment_request(
    payment_token: str = "cnon:card-nonce-ok",
    amount: int = 2999,
    currency: str = "GBP",
    idempotency_key: str | None = None,
    phone: str | None = "+44123456789",
) -> PaymentRequest:
    """Create a test payment request."""
    return PaymentRequest(
        payment_token=payment_token,
        amount=amount,
        currency=currency,
        customer=CustomerDetails(
            email="test@example.com",
            phone=phone,
        ),
        shipping_address=ShippingAddress(
            first_name="John",
            last_name="Doe",
            address_line1="123 Test Street",
            address_line2="Apt 4B",
            city="London",
            county="Greater London",
            postcode="SW1A 1AA",
            country="GB",
        ),
        shipping_method="standard",
        shipping_cost=499,
        items=[
            CartItem(
                product_id=uuid4(),
                name="Test Product",
                quantity=1,
                price=2500,
            )
        ],
        idempotency_key=idempotency_key,
    )


def create_mock_settings():
    """Create mock settings for tests."""
    return MagicMock(
        square_access_token="test-token",
        square_environment="sandbox",
        square_location_id="test-location",
        square_webhook_signature_key="test-webhook-key",
    )


def create_mock_success_response(payment_id="payment123", status="COMPLETED", amount=2999):
    """Create a mock successful payment response."""
    mock_response = MagicMock()
    mock_response.is_success.return_value = True
    mock_response.body = {
        "payment": {
            "id": payment_id,
            "status": status,
            "amount_money": {"amount": amount, "currency": "GBP"},
            "receipt_url": f"https://squareup.com/receipt/{payment_id}",
        }
    }
    return mock_response


def create_mock_error_response(error_code="PAYMENT_FAILED", detail="Error occurred"):
    """Create a mock error payment response."""
    mock_response = MagicMock()
    mock_response.is_success.return_value = False
    mock_response.errors = [{"code": error_code, "detail": detail}]
    return mock_response


# ============================================
# Test: Service Initialization
# ============================================


class TestSquarePaymentServiceInit:
    """Tests for SquarePaymentService initialization."""

    def test_init_creates_client_with_correct_params(self):
        """Test that initialization creates Square client with correct parameters."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_client_instance = MagicMock()
                mock_client.return_value = mock_client_instance

                service = SquarePaymentService()

                mock_client.assert_called_once_with(
                    access_token="test-token",
                    environment="sandbox",
                )
                assert service.location_id == "test-location"
                assert service.environment == "sandbox"
                assert service.payments_api == mock_client_instance.payments
                assert service.refunds_api == mock_client_instance.refunds

    def test_init_sets_retry_configuration(self):
        """Test that initialization sets retry configuration."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client"):
                service = SquarePaymentService()

                assert service.MAX_RETRIES == 3
                assert service.INITIAL_RETRY_DELAY == 1.0
                assert service.MAX_RETRY_DELAY == 10.0
                assert service.BACKOFF_MULTIPLIER == 2.0


# ============================================
# Test: Error Code Mapping
# ============================================


class TestErrorCodeMapping:
    """Tests for Square error code mapping to user-friendly messages."""

    @pytest.mark.parametrize(
        "error_code,expected_phrase",
        [
            ("CARD_DECLINED", "declined"),
            ("CARD_DECLINED_CALL_ISSUER", "contact your card issuer"),
            ("CARD_DECLINED_VERIFICATION_REQUIRED", "verification required"),
            ("INVALID_CARD", "invalid"),
            ("INVALID_CARD_DATA", "invalid"),
            ("CARD_EXPIRED", "expired"),
            ("CARD_NOT_SUPPORTED", "not supported"),
            ("CVV_FAILURE", "cvv"),
            ("INVALID_CVV", "cvv"),
            ("ADDRESS_VERIFICATION_FAILURE", "address verification"),
            ("INVALID_POSTAL_CODE", "postal code"),
            ("INSUFFICIENT_FUNDS", "insufficient funds"),
            ("TRANSACTION_LIMIT", "limit exceeded"),
            ("GENERIC_DECLINE", "declined"),
            ("PAN_FAILURE", "card number"),
            ("EXPIRATION_FAILURE", "expiration"),
            ("INVALID_ACCOUNT", "invalid account"),
            ("CARD_TOKEN_EXPIRED", "session expired"),
            ("CARD_TOKEN_USED", "token already used"),
            ("GATEWAY_TIMEOUT", "timeout"),
            ("TEMPORARILY_UNAVAILABLE", "temporarily unavailable"),
            ("INTERNAL_SERVER_ERROR", "server error"),
        ],
    )
    def test_error_code_returns_user_friendly_message(self, error_code, expected_phrase):
        """Test that each error code returns appropriate user-friendly message."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_client.return_value = MagicMock()
                service = SquarePaymentService()

                message = service._get_user_friendly_message(error_code)
                assert expected_phrase.lower() in message.lower()

    def test_unknown_error_code_returns_generic_message(self):
        """Test that unknown error code returns generic user-friendly message."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_client.return_value = MagicMock()
                service = SquarePaymentService()

                message = service._get_user_friendly_message("UNKNOWN_ERROR_XYZ")
                assert "could not be processed" in message.lower()

    def test_all_square_error_messages_defined(self):
        """Test that all expected Square error codes have messages defined."""
        expected_codes = [
            "CARD_DECLINED",
            "CARD_DECLINED_CALL_ISSUER",
            "CARD_DECLINED_VERIFICATION_REQUIRED",
            "INVALID_CARD",
            "INVALID_CARD_DATA",
            "CARD_EXPIRED",
            "CARD_NOT_SUPPORTED",
            "CVV_FAILURE",
            "INVALID_CVV",
            "ADDRESS_VERIFICATION_FAILURE",
            "INVALID_POSTAL_CODE",
            "INSUFFICIENT_FUNDS",
            "TRANSACTION_LIMIT",
            "GENERIC_DECLINE",
            "PAN_FAILURE",
            "EXPIRATION_FAILURE",
            "INVALID_ACCOUNT",
            "CARD_TOKEN_EXPIRED",
            "CARD_TOKEN_USED",
            "GATEWAY_TIMEOUT",
            "TEMPORARILY_UNAVAILABLE",
            "INTERNAL_SERVER_ERROR",
        ]
        for code in expected_codes:
            assert code in SQUARE_ERROR_MESSAGES, f"Missing error message for {code}"


# ============================================
# Test: Retriable Error Detection
# ============================================


class TestRetriableErrorDetection:
    """Tests for retriable error detection."""

    @pytest.mark.parametrize(
        "error_code",
        [
            "GATEWAY_TIMEOUT",
            "TEMPORARILY_UNAVAILABLE",
            "INTERNAL_SERVER_ERROR",
            "SERVICE_UNAVAILABLE",
            "TIMEOUT",
        ],
    )
    def test_retriable_error_codes_detected(self, error_code):
        """Test that retriable error codes are correctly identified."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_client.return_value = MagicMock()
                service = SquarePaymentService()

                assert service._is_retriable_error(error_code) is True

    @pytest.mark.parametrize(
        "error_code",
        ["CARD_DECLINED", "INVALID_CARD", "CVV_FAILURE", "INSUFFICIENT_FUNDS"],
    )
    def test_non_retriable_error_codes_not_detected(self, error_code):
        """Test that non-retriable error codes are not marked as retriable."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_client.return_value = MagicMock()
                service = SquarePaymentService()

                assert service._is_retriable_error(error_code) is False

    @pytest.mark.parametrize(
        "exception_message",
        ["Connection timeout", "Network error", "Temporary failure", "connection refused"],
    )
    def test_network_exceptions_are_retriable(self, exception_message):
        """Test that network-related exceptions are marked as retriable."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_client.return_value = MagicMock()
                service = SquarePaymentService()

                exception = Exception(exception_message)
                assert service._is_retriable_error("", exception) is True

    def test_non_network_exceptions_not_retriable(self):
        """Test that non-network exceptions are not retriable."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_client.return_value = MagicMock()
                service = SquarePaymentService()

                exception = Exception("Invalid JSON format")
                assert service._is_retriable_error("", exception) is False


# ============================================
# Test: Retry Delay Calculation
# ============================================


class TestRetryDelayCalculation:
    """Tests for retry delay calculation with exponential backoff."""

    def test_first_retry_delay(self):
        """Test that first retry delay equals initial delay."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_client.return_value = MagicMock()
                service = SquarePaymentService()

                delay = service._calculate_retry_delay(0)
                assert delay == service.INITIAL_RETRY_DELAY

    def test_second_retry_delay_doubles(self):
        """Test that second retry delay doubles."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_client.return_value = MagicMock()
                service = SquarePaymentService()

                delay = service._calculate_retry_delay(1)
                expected = service.INITIAL_RETRY_DELAY * service.BACKOFF_MULTIPLIER
                assert delay == expected

    def test_third_retry_delay_quadruples(self):
        """Test that third retry delay quadruples."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_client.return_value = MagicMock()
                service = SquarePaymentService()

                delay = service._calculate_retry_delay(2)
                expected = service.INITIAL_RETRY_DELAY * (service.BACKOFF_MULTIPLIER**2)
                assert delay == expected

    def test_delay_capped_at_max(self):
        """Test that delay is capped at maximum value."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_client.return_value = MagicMock()
                service = SquarePaymentService()

                # Very high attempt number should still cap at max
                delay = service._calculate_retry_delay(100)
                assert delay == service.MAX_RETRY_DELAY


# ============================================
# Test: Process Payment - Success Cases
# ============================================


class TestProcessPaymentSuccess:
    """Tests for successful payment processing."""

    def test_process_payment_success_returns_response(self):
        """Test successful payment returns PaymentResponse."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = create_mock_success_response()
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.process_payment(create_payment_request())

                assert isinstance(result, PaymentResponse)
                assert result.success is True
                assert result.payment_id == "payment123"
                assert result.status == "COMPLETED"
                assert result.amount == 2999
                assert result.currency == "GBP"

    def test_process_payment_success_includes_receipt_url(self):
        """Test successful payment includes receipt URL."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = create_mock_success_response()
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.process_payment(create_payment_request())

                assert result.receipt_url == "https://squareup.com/receipt/payment123"

    def test_process_payment_generates_order_id(self):
        """Test successful payment generates order ID from payment ID."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = create_mock_success_response(
                    payment_id="abcd1234efgh5678"
                )
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.process_payment(create_payment_request())

                assert result.order_id == "MF-ABCD1234"

    def test_process_payment_without_phone(self):
        """Test successful payment without phone number."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = create_mock_success_response()
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                request = create_payment_request(phone=None)
                service.process_payment(request)

                call_body = mock_payments_api.create_payment.call_args[1]["body"]
                assert "buyer_phone_number" not in call_body

    def test_process_payment_with_phone(self):
        """Test successful payment includes phone number when provided."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = create_mock_success_response()
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                request = create_payment_request(phone="+44123456789")
                service.process_payment(request)

                call_body = mock_payments_api.create_payment.call_args[1]["body"]
                assert call_body["buyer_phone_number"] == "+44123456789"


# ============================================
# Test: Process Payment - Idempotency
# ============================================


class TestProcessPaymentIdempotency:
    """Tests for payment idempotency key handling."""

    def test_uses_provided_idempotency_key(self):
        """Test that provided idempotency key is used."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = create_mock_success_response()
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                request = create_payment_request(idempotency_key="custom-key-12345")
                service.process_payment(request)

                call_body = mock_payments_api.create_payment.call_args[1]["body"]
                assert call_body["idempotency_key"] == "custom-key-12345"

    def test_generates_uuid_when_no_idempotency_key(self):
        """Test that UUID is generated when no idempotency key provided."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = create_mock_success_response()
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                request = create_payment_request(idempotency_key=None)
                service.process_payment(request)

                call_body = mock_payments_api.create_payment.call_args[1]["body"]
                assert len(call_body["idempotency_key"]) == 36  # UUID format


# ============================================
# Test: Process Payment - Request Body
# ============================================


class TestProcessPaymentRequestBody:
    """Tests for payment request body construction."""

    def test_request_body_includes_all_required_fields(self):
        """Test that request body includes all required fields."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = create_mock_success_response()
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                service.process_payment(create_payment_request())

                call_body = mock_payments_api.create_payment.call_args[1]["body"]

                assert call_body["source_id"] == "cnon:card-nonce-ok"
                assert call_body["amount_money"]["amount"] == 2999
                assert call_body["amount_money"]["currency"] == "GBP"
                assert call_body["location_id"] == "test-location"
                assert call_body["buyer_email_address"] == "test@example.com"
                assert "idempotency_key" in call_body
                assert "reference_id" in call_body
                assert "note" in call_body

    def test_request_body_includes_shipping_address(self):
        """Test that request body includes complete shipping address."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = create_mock_success_response()
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                service.process_payment(create_payment_request())

                call_body = mock_payments_api.create_payment.call_args[1]["body"]
                shipping = call_body["shipping_address"]

                assert shipping["address_line_1"] == "123 Test Street"
                assert shipping["address_line_2"] == "Apt 4B"
                assert shipping["locality"] == "London"
                assert shipping["administrative_district_level_1"] == "Greater London"
                assert shipping["postal_code"] == "SW1A 1AA"
                assert shipping["country"] == "GB"
                assert shipping["first_name"] == "John"
                assert shipping["last_name"] == "Doe"

    def test_reference_id_includes_mystmere_prefix(self):
        """Test that reference ID includes mystmere prefix."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = create_mock_success_response()
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                service.process_payment(create_payment_request())

                call_body = mock_payments_api.create_payment.call_args[1]["body"]
                assert call_body["reference_id"].startswith("mystmere-")

    def test_note_includes_item_count(self):
        """Test that note includes item count."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = create_mock_success_response()
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                service.process_payment(create_payment_request())

                call_body = mock_payments_api.create_payment.call_args[1]["body"]
                assert "1 item(s)" in call_body["note"]


# ============================================
# Test: Process Payment - Failure Cases
# ============================================


class TestProcessPaymentFailure:
    """Tests for payment failure handling."""

    def test_payment_failure_returns_error(self):
        """Test that payment failure returns PaymentError."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = create_mock_error_response(
                    "CARD_DECLINED", "Card declined"
                )
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.process_payment(create_payment_request())

                assert isinstance(result, PaymentError)
                assert result.success is False
                assert result.error_code == "CARD_DECLINED"

    def test_payment_failure_includes_user_friendly_message(self):
        """Test that payment failure includes user-friendly message."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = create_mock_error_response(
                    "CARD_DECLINED", "Card declined"
                )
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.process_payment(create_payment_request())

                assert "declined" in result.error_message.lower()

    def test_payment_failure_with_no_errors_array(self):
        """Test payment failure when errors array is None."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.is_success.return_value = False
                mock_response.errors = None

                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = mock_response
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.process_payment(create_payment_request())

                assert isinstance(result, PaymentError)
                assert result.error_code == "PAYMENT_FAILED"

    def test_payment_failure_with_empty_errors_array(self):
        """Test payment failure when errors array is empty."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.is_success.return_value = False
                mock_response.errors = []

                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = mock_response
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.process_payment(create_payment_request())

                assert isinstance(result, PaymentError)
                assert result.error_code == "PAYMENT_FAILED"

    def test_payment_exception_returns_error(self):
        """Test that exception during payment returns PaymentError."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.side_effect = Exception("API connection failed")
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.process_payment(create_payment_request())

                assert isinstance(result, PaymentError)
                assert result.error_code == "PAYMENT_EXCEPTION"
                assert "API connection failed" in result.detail


# ============================================
# Test: Process Payment - Retry Logic
# ============================================


class TestProcessPaymentRetry:
    """Tests for payment retry logic."""

    def test_retry_on_gateway_timeout_success(self):
        """Test successful retry after gateway timeout."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                with patch("app.services.square_payment.time.sleep"):
                    mock_payments_api = MagicMock()
                    mock_payments_api.create_payment.side_effect = [
                        create_mock_error_response("GATEWAY_TIMEOUT", "Timeout"),
                        create_mock_success_response(),
                    ]
                    mock_client.return_value.payments = mock_payments_api

                    service = SquarePaymentService()
                    result = service.process_payment(create_payment_request())

                    assert isinstance(result, PaymentResponse)
                    assert result.success is True
                    assert mock_payments_api.create_payment.call_count == 2

    def test_retry_on_temporarily_unavailable(self):
        """Test retry on TEMPORARILY_UNAVAILABLE error."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                with patch("app.services.square_payment.time.sleep"):
                    mock_payments_api = MagicMock()
                    mock_payments_api.create_payment.side_effect = [
                        create_mock_error_response("TEMPORARILY_UNAVAILABLE", "Try again"),
                        create_mock_success_response(),
                    ]
                    mock_client.return_value.payments = mock_payments_api

                    service = SquarePaymentService()
                    result = service.process_payment(create_payment_request())

                    assert result.success is True
                    assert mock_payments_api.create_payment.call_count == 2

    def test_retry_on_internal_server_error(self):
        """Test retry on INTERNAL_SERVER_ERROR."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                with patch("app.services.square_payment.time.sleep"):
                    mock_payments_api = MagicMock()
                    mock_payments_api.create_payment.side_effect = [
                        create_mock_error_response("INTERNAL_SERVER_ERROR", "Server error"),
                        create_mock_success_response(),
                    ]
                    mock_client.return_value.payments = mock_payments_api

                    service = SquarePaymentService()
                    result = service.process_payment(create_payment_request())

                    assert result.success is True
                    assert mock_payments_api.create_payment.call_count == 2

    def test_retry_on_connection_exception(self):
        """Test retry on connection exception."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                with patch("app.services.square_payment.time.sleep"):
                    mock_payments_api = MagicMock()
                    mock_payments_api.create_payment.side_effect = [
                        Exception("Connection timeout"),
                        create_mock_success_response(),
                    ]
                    mock_client.return_value.payments = mock_payments_api

                    service = SquarePaymentService()
                    result = service.process_payment(create_payment_request())

                    assert result.success is True
                    assert mock_payments_api.create_payment.call_count == 2

    def test_no_retry_on_card_declined(self):
        """Test no retry on CARD_DECLINED error."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = create_mock_error_response(
                    "CARD_DECLINED", "Declined"
                )
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.process_payment(create_payment_request())

                assert isinstance(result, PaymentError)
                assert mock_payments_api.create_payment.call_count == 1

    def test_no_retry_on_cvv_failure(self):
        """Test no retry on CVV_FAILURE error."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.return_value = create_mock_error_response(
                    "CVV_FAILURE", "CVV mismatch"
                )
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.process_payment(create_payment_request())

                assert isinstance(result, PaymentError)
                assert mock_payments_api.create_payment.call_count == 1

    def test_no_retry_on_non_network_exception(self):
        """Test no retry on non-network exception."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.create_payment.side_effect = Exception("Invalid JSON format")
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.process_payment(create_payment_request())

                assert isinstance(result, PaymentError)
                assert mock_payments_api.create_payment.call_count == 1

    def test_max_retries_exhausted(self):
        """Test that retries stop after MAX_RETRIES."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                with patch("app.services.square_payment.time.sleep"):
                    mock_payments_api = MagicMock()
                    mock_payments_api.create_payment.return_value = create_mock_error_response(
                        "GATEWAY_TIMEOUT", "Timeout"
                    )
                    mock_client.return_value.payments = mock_payments_api

                    service = SquarePaymentService()
                    result = service.process_payment(create_payment_request())

                    assert isinstance(result, PaymentError)
                    assert mock_payments_api.create_payment.call_count == service.MAX_RETRIES

    def test_retry_calls_sleep_with_correct_delay(self):
        """Test that retry calls sleep with correct exponential delay."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                with patch("app.services.square_payment.time.sleep") as mock_sleep:
                    mock_payments_api = MagicMock()
                    mock_payments_api.create_payment.side_effect = [
                        create_mock_error_response("GATEWAY_TIMEOUT", "Timeout"),
                        create_mock_error_response("GATEWAY_TIMEOUT", "Timeout"),
                        create_mock_success_response(),
                    ]
                    mock_client.return_value.payments = mock_payments_api

                    service = SquarePaymentService()
                    service.process_payment(create_payment_request())

                    # Check sleep was called with exponential delays
                    assert mock_sleep.call_count == 2
                    mock_sleep.assert_any_call(1.0)  # First delay
                    mock_sleep.assert_any_call(2.0)  # Second delay (1.0 * 2)


# ============================================
# Test: Get Payment
# ============================================


class TestGetPayment:
    """Tests for get_payment method."""

    def test_get_payment_success(self):
        """Test successful payment retrieval."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.is_success.return_value = True
                mock_response.body = {
                    "payment": {
                        "id": "payment123",
                        "status": "COMPLETED",
                        "amount_money": {"amount": 5000, "currency": "GBP"},
                    }
                }

                mock_payments_api = MagicMock()
                mock_payments_api.get_payment.return_value = mock_response
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.get_payment("payment123")

                assert result is not None
                assert result["id"] == "payment123"
                assert result["status"] == "COMPLETED"
                mock_payments_api.get_payment.assert_called_once_with(payment_id="payment123")

    def test_get_payment_not_found(self):
        """Test payment not found returns None."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.is_success.return_value = False
                mock_response.errors = [{"code": "NOT_FOUND"}]

                mock_payments_api = MagicMock()
                mock_payments_api.get_payment.return_value = mock_response
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.get_payment("nonexistent")

                assert result is None

    def test_get_payment_exception(self):
        """Test get_payment exception returns None."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.get_payment.side_effect = Exception("API error")
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.get_payment("payment123")

                assert result is None


# ============================================
# Test: Refund Payment
# ============================================


class TestRefundPayment:
    """Tests for refund_payment method."""

    def test_refund_payment_success(self):
        """Test successful payment refund."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.is_success.return_value = True
                mock_response.body = {
                    "refund": {
                        "id": "refund123",
                        "status": "COMPLETED",
                        "amount_money": {"amount": 2999, "currency": "GBP"},
                    }
                }

                mock_refunds_api = MagicMock()
                mock_refunds_api.refund_payment.return_value = mock_response
                mock_client.return_value.payments = MagicMock()
                mock_client.return_value.refunds = mock_refunds_api

                service = SquarePaymentService()
                result = service.refund_payment(
                    payment_id="payment123",
                    amount=2999,
                    currency="GBP",
                    reason="Customer request",
                )

                assert result["success"] is True
                assert result["refund_id"] == "refund123"
                assert result["status"] == "COMPLETED"
                assert result["amount"] == 2999
                assert result["currency"] == "GBP"

    def test_refund_payment_partial_amount(self):
        """Test partial refund with specific amount."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.is_success.return_value = True
                mock_response.body = {
                    "refund": {
                        "id": "refund456",
                        "status": "COMPLETED",
                        "amount_money": {"amount": 1500, "currency": "GBP"},
                    }
                }

                mock_refunds_api = MagicMock()
                mock_refunds_api.refund_payment.return_value = mock_response
                mock_client.return_value.payments = MagicMock()
                mock_client.return_value.refunds = mock_refunds_api

                service = SquarePaymentService()
                result = service.refund_payment(
                    payment_id="payment123",
                    amount=1500,
                )

                assert result["success"] is True
                assert result["amount"] == 1500

    def test_refund_payment_with_reason(self):
        """Test refund includes reason in request."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.is_success.return_value = True
                mock_response.body = {
                    "refund": {
                        "id": "refund789",
                        "status": "COMPLETED",
                        "amount_money": {"amount": 1000, "currency": "GBP"},
                    }
                }

                mock_refunds_api = MagicMock()
                mock_refunds_api.refund_payment.return_value = mock_response
                mock_client.return_value.payments = MagicMock()
                mock_client.return_value.refunds = mock_refunds_api

                service = SquarePaymentService()
                service.refund_payment(
                    payment_id="payment123",
                    amount=1000,
                    reason="Defective product",
                )

                call_body = mock_refunds_api.refund_payment.call_args[1]["body"]
                assert call_body["reason"] == "Defective product"

    def test_refund_payment_with_custom_idempotency_key(self):
        """Test refund uses custom idempotency key when provided."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.is_success.return_value = True
                mock_response.body = {
                    "refund": {
                        "id": "refund101",
                        "status": "COMPLETED",
                        "amount_money": {"amount": 500, "currency": "GBP"},
                    }
                }

                mock_refunds_api = MagicMock()
                mock_refunds_api.refund_payment.return_value = mock_response
                mock_client.return_value.payments = MagicMock()
                mock_client.return_value.refunds = mock_refunds_api

                service = SquarePaymentService()
                service.refund_payment(
                    payment_id="payment123",
                    amount=500,
                    idempotency_key="custom-refund-key",
                )

                call_body = mock_refunds_api.refund_payment.call_args[1]["body"]
                assert call_body["idempotency_key"] == "custom-refund-key"

    def test_refund_payment_generates_idempotency_key(self):
        """Test refund generates idempotency key when not provided."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.is_success.return_value = True
                mock_response.body = {
                    "refund": {
                        "id": "refund202",
                        "status": "COMPLETED",
                        "amount_money": {"amount": 800, "currency": "GBP"},
                    }
                }

                mock_refunds_api = MagicMock()
                mock_refunds_api.refund_payment.return_value = mock_response
                mock_client.return_value.payments = MagicMock()
                mock_client.return_value.refunds = mock_refunds_api

                service = SquarePaymentService()
                service.refund_payment(payment_id="payment123", amount=800)

                call_body = mock_refunds_api.refund_payment.call_args[1]["body"]
                assert call_body["idempotency_key"].startswith("refund-payment123-")

    def test_refund_payment_failure(self):
        """Test refund payment failure returns error."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.is_success.return_value = False
                mock_response.errors = [{"code": "INVALID_PAYMENT_ID", "detail": "Not found"}]

                mock_refunds_api = MagicMock()
                mock_refunds_api.refund_payment.return_value = mock_response
                mock_client.return_value.payments = MagicMock()
                mock_client.return_value.refunds = mock_refunds_api

                service = SquarePaymentService()
                result = service.refund_payment(payment_id="invalid", amount=1000)

                assert result["success"] is False
                assert result["error_code"] == "INVALID_PAYMENT_ID"

    def test_refund_payment_failure_no_errors(self):
        """Test refund payment failure with no errors array."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.is_success.return_value = False
                mock_response.errors = None

                mock_refunds_api = MagicMock()
                mock_refunds_api.refund_payment.return_value = mock_response
                mock_client.return_value.payments = MagicMock()
                mock_client.return_value.refunds = mock_refunds_api

                service = SquarePaymentService()
                result = service.refund_payment(payment_id="payment123", amount=1000)

                assert result["success"] is False
                assert result["error_code"] == "REFUND_FAILED"

    def test_refund_payment_exception(self):
        """Test refund payment exception handling."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_refunds_api = MagicMock()
                mock_refunds_api.refund_payment.side_effect = Exception("Network error")
                mock_client.return_value.payments = MagicMock()
                mock_client.return_value.refunds = mock_refunds_api

                service = SquarePaymentService()
                result = service.refund_payment(payment_id="payment123", amount=1000)

                assert result["success"] is False
                assert result["error_code"] == "REFUND_EXCEPTION"
                assert "Network error" in result["detail"]


# ============================================
# Test: List Payments
# ============================================


class TestListPayments:
    """Tests for list_payments method."""

    def test_list_payments_success(self):
        """Test successful payment listing."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.is_success.return_value = True
                mock_response.body = {
                    "payments": [
                        {"id": "payment1", "status": "COMPLETED"},
                        {"id": "payment2", "status": "COMPLETED"},
                    ]
                }

                mock_payments_api = MagicMock()
                mock_payments_api.list_payments.return_value = mock_response
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.list_payments()

                assert len(result) == 2
                assert result[0]["id"] == "payment1"
                assert result[1]["id"] == "payment2"

    def test_list_payments_with_time_range(self):
        """Test payment listing with time range parameters."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.is_success.return_value = True
                mock_response.body = {"payments": [{"id": "payment1"}]}

                mock_payments_api = MagicMock()
                mock_payments_api.list_payments.return_value = mock_response
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                service.list_payments(
                    begin_time="2025-01-01T00:00:00Z",
                    end_time="2025-01-31T23:59:59Z",
                    limit=50,
                )

                mock_payments_api.list_payments.assert_called_once_with(
                    location_id="test-location",
                    begin_time="2025-01-01T00:00:00Z",
                    end_time="2025-01-31T23:59:59Z",
                    limit=50,
                )

    def test_list_payments_failure(self):
        """Test payment listing failure returns empty list."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_response = MagicMock()
                mock_response.is_success.return_value = False
                mock_response.errors = [{"code": "ERROR"}]

                mock_payments_api = MagicMock()
                mock_payments_api.list_payments.return_value = mock_response
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.list_payments()

                assert result == []

    def test_list_payments_exception(self):
        """Test payment listing exception returns empty list."""
        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client") as mock_client:
                mock_payments_api = MagicMock()
                mock_payments_api.list_payments.side_effect = Exception("API error")
                mock_client.return_value.payments = mock_payments_api

                service = SquarePaymentService()
                result = service.list_payments()

                assert result == []


# ============================================
# Test: Singleton Pattern
# ============================================


class TestPaymentServiceSingleton:
    """Tests for payment service singleton pattern."""

    def test_get_payment_service_creates_singleton(self):
        """Test that get_payment_service returns the same instance."""
        reset_payment_service()

        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client"):
                service1 = get_payment_service()
                service2 = get_payment_service()

                assert service1 is service2

        reset_payment_service()

    def test_reset_payment_service_clears_singleton(self):
        """Test that reset_payment_service clears the singleton."""
        reset_payment_service()

        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client"):
                service1 = get_payment_service()
                reset_payment_service()
                service2 = get_payment_service()

                assert service1 is not service2

        reset_payment_service()

    def test_get_payment_service_returns_correct_type(self):
        """Test that get_payment_service returns SquarePaymentService."""
        reset_payment_service()

        with patch("app.services.square_payment.get_settings") as mock_settings:
            mock_settings.return_value = create_mock_settings()
            with patch("app.services.square_payment.Client"):
                service = get_payment_service()

                assert isinstance(service, SquarePaymentService)

        reset_payment_service()
