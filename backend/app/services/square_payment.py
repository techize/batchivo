"""Square payment processing service with enhanced error handling and retry logic."""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from square import Square
from square.core.api_error import ApiError

from app.config import get_settings
from app.schemas.payment import PaymentRequest, PaymentResponse, PaymentError

logger = logging.getLogger(__name__)


# User-friendly error messages for Square API error codes
SQUARE_ERROR_MESSAGES = {
    # Card errors
    "CARD_DECLINED": "Your card was declined. Please try another card.",
    "CARD_DECLINED_CALL_ISSUER": "Your card was declined. Please contact your card issuer.",
    "CARD_DECLINED_VERIFICATION_REQUIRED": "Additional verification required. Please try again.",
    "INVALID_CARD": "Card details are invalid. Please check and try again.",
    "INVALID_CARD_DATA": "Card details are invalid. Please check and try again.",
    "CARD_EXPIRED": "Your card has expired. Please use a different card.",
    "CARD_NOT_SUPPORTED": "This card type is not supported. Please try another card.",
    # CVV errors
    "CVV_FAILURE": "CVV verification failed. Please check the security code.",
    "INVALID_CVV": "Invalid CVV. Please check the security code on your card.",
    # Address verification
    "ADDRESS_VERIFICATION_FAILURE": "Address verification failed. Please check your billing address.",
    "INVALID_POSTAL_CODE": "Invalid postal code. Please check your billing address.",
    # Funds
    "INSUFFICIENT_FUNDS": "Insufficient funds. Please try another card.",
    "TRANSACTION_LIMIT": "Transaction limit exceeded. Please try a smaller amount or another card.",
    # Processing errors
    "GENERIC_DECLINE": "Your payment was declined. Please try another card.",
    "PAN_FAILURE": "Card number verification failed. Please check the card number.",
    "EXPIRATION_FAILURE": "Card expiration date is invalid. Please check and try again.",
    "INVALID_ACCOUNT": "Invalid account. Please try another card.",
    "CARD_TOKEN_EXPIRED": "Payment session expired. Please refresh and try again.",
    "CARD_TOKEN_USED": "Payment token already used. Please refresh and try again.",
    # Network/temporary errors (retriable)
    "GATEWAY_TIMEOUT": "Payment gateway timeout. Please try again.",
    "TEMPORARILY_UNAVAILABLE": "Payment service temporarily unavailable. Please try again.",
    "INTERNAL_SERVER_ERROR": "A server error occurred. Please try again.",
}

# Error codes that indicate temporary/network issues (worth retrying)
RETRIABLE_ERROR_CODES = {
    "GATEWAY_TIMEOUT",
    "TEMPORARILY_UNAVAILABLE",
    "INTERNAL_SERVER_ERROR",
    "SERVICE_UNAVAILABLE",
    "TIMEOUT",
}


class SquarePaymentService:
    """Service for processing payments via Square API with retry logic."""

    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1.0  # seconds
    MAX_RETRY_DELAY = 10.0  # seconds
    BACKOFF_MULTIPLIER = 2.0

    def __init__(
        self,
        access_token: str | None = None,
        location_id: str | None = None,
        environment: str | None = None,
    ):
        """Initialize Square client.

        Args:
            access_token: Square API access token (uses env var if not provided)
            location_id: Square location ID (uses env var if not provided)
            environment: Square environment 'sandbox' or 'production' (uses env var if not provided)
        """
        settings = get_settings()

        # Use provided credentials or fall back to env vars
        self._access_token = access_token or settings.square_access_token
        self.location_id = location_id or settings.square_location_id
        self.environment = environment or settings.square_environment

        self.client = Square(
            token=self._access_token,
            environment=self.environment,
        )

    def _get_user_friendly_message(self, error_code: str, detail: str = "") -> str:
        """Map Square error code to user-friendly message."""
        if error_code in SQUARE_ERROR_MESSAGES:
            return SQUARE_ERROR_MESSAGES[error_code]
        # Return a generic message for unknown error codes
        return "Payment could not be processed. Please try again or use a different card."

    def _is_retriable_error(self, error_code: str, exception: Exception = None) -> bool:
        """Check if error is retriable (network/temporary issues)."""
        if error_code in RETRIABLE_ERROR_CODES:
            return True
        # Also retry on connection errors
        if exception:
            error_str = str(exception).lower()
            return any(
                term in error_str for term in ["timeout", "connection", "network", "temporary"]
            )
        return False

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate delay before next retry with exponential backoff."""
        delay = self.INITIAL_RETRY_DELAY * (self.BACKOFF_MULTIPLIER**attempt)
        return min(delay, self.MAX_RETRY_DELAY)

    def process_payment(
        self,
        request: PaymentRequest,
    ) -> PaymentResponse | PaymentError:
        """
        Process a payment using a token from Square Web Payments SDK.

        Includes retry logic for network/temporary errors with exponential backoff.

        Args:
            request: Payment request with token and order details

        Returns:
            PaymentResponse on success, PaymentError on failure
        """
        # Use provided idempotency key or generate one
        idempotency_key = request.idempotency_key or str(uuid.uuid4())

        # Build the payment request body
        body = {
            "source_id": request.payment_token,
            "idempotency_key": idempotency_key,
            "amount_money": {
                "amount": request.amount,
                "currency": request.currency,
            },
            "location_id": self.location_id,
            "buyer_email_address": request.customer.email,
            "reference_id": f"mystmere-{idempotency_key[:8]}",
            "note": f"Mystmereforge order - {len(request.items)} item(s)",
            "shipping_address": {
                "address_line_1": request.shipping_address.address_line1,
                "address_line_2": request.shipping_address.address_line2 or "",
                "locality": request.shipping_address.city,
                "administrative_district_level_1": request.shipping_address.county or "",
                "postal_code": request.shipping_address.postcode,
                "country": request.shipping_address.country,
                "first_name": request.shipping_address.first_name,
                "last_name": request.shipping_address.last_name,
            },
        }

        if request.customer.phone:
            # Format phone to E.164 for Square (e.g., +441234567890)
            phone = request.customer.phone.strip()
            # Remove common formatting characters
            phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
            # Convert UK numbers: 07xxx -> +447xxx, 01xxx -> +441xxx
            if phone.startswith("0") and len(phone) >= 10:
                phone = "+44" + phone[1:]
            # Only send if it looks like a valid E.164 number
            if phone.startswith("+") and len(phone) >= 10:
                body["buyer_phone_number"] = phone

        last_error = None
        last_error_code = "PAYMENT_FAILED"

        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(
                    f"Processing payment attempt {attempt + 1}/{self.MAX_RETRIES} "
                    f"idempotency_key={idempotency_key}"
                )

                result = self.client.payments.create(**body)
                payment = result.payment

                logger.info(
                    f"Payment successful: payment_id={payment.id} "
                    f"status={payment.status} amount={request.amount}"
                )
                return PaymentResponse(
                    success=True,
                    order_id=f"MF-{(payment.id or '')[:8].upper()}",
                    payment_id=payment.id or "",
                    amount=payment.amount_money.amount if payment.amount_money else 0,
                    currency=payment.amount_money.currency if payment.amount_money else "GBP",
                    status=payment.status or "UNKNOWN",
                    receipt_url=payment.receipt_url,
                    created_at=datetime.now(timezone.utc),
                )

            except ApiError as e:
                # Payment failed via API error
                errors = e.errors or []
                error_code = errors[0].code if errors else "PAYMENT_FAILED"
                error_detail = errors[0].detail if errors else ""

                logger.warning(
                    f"Payment failed: error_code={error_code} "
                    f"detail={error_detail} attempt={attempt + 1}"
                )

                last_error_code = error_code
                last_error = error_detail

                # Only retry on retriable errors
                if self._is_retriable_error(error_code) and attempt < self.MAX_RETRIES - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"Retrying payment in {delay:.1f}s...")
                    time.sleep(delay)
                    continue

                # Non-retriable error - return immediately
                return PaymentError(
                    success=False,
                    error_code=error_code,
                    error_message=self._get_user_friendly_message(error_code, error_detail),
                    detail=str(errors),
                )

            except Exception as e:
                logger.error(f"Payment exception: {e} attempt={attempt + 1}")
                last_error = str(e)
                last_error_code = "PAYMENT_EXCEPTION"

                # Retry on network exceptions
                if self._is_retriable_error("", e) and attempt < self.MAX_RETRIES - 1:
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"Retrying payment after exception in {delay:.1f}s...")
                    time.sleep(delay)
                    continue

                return PaymentError(
                    success=False,
                    error_code="PAYMENT_EXCEPTION",
                    error_message="An unexpected error occurred. Please try again.",
                    detail=str(e),
                )

        # All retries exhausted
        logger.error(f"Payment failed after {self.MAX_RETRIES} attempts")
        return PaymentError(
            success=False,
            error_code=last_error_code,
            error_message=self._get_user_friendly_message(last_error_code, last_error or ""),
            detail=last_error or "Payment failed after multiple attempts",
        )

    def get_payment(self, payment_id: str) -> Optional[dict]:
        """
        Retrieve a payment by ID.

        Args:
            payment_id: Square payment ID

        Returns:
            Payment details dict or None if not found
        """
        try:
            result = self.client.payments.get(payment_id=payment_id)
            payment = result.payment
            if payment:
                return {
                    "id": payment.id,
                    "status": payment.status,
                    "amount_money": {
                        "amount": payment.amount_money.amount if payment.amount_money else 0,
                        "currency": payment.amount_money.currency
                        if payment.amount_money
                        else "GBP",
                    },
                    "receipt_url": payment.receipt_url,
                    "created_at": payment.created_at,
                }
            return None
        except ApiError as e:
            logger.warning(f"Failed to get payment {payment_id}: {e.errors}")
            return None
        except Exception as e:
            logger.error(f"Exception getting payment {payment_id}: {e}")
            return None

    def refund_payment(
        self,
        payment_id: str,
        amount: int,
        currency: str = "GBP",
        reason: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> dict:
        """
        Refund a payment (full or partial).

        Args:
            payment_id: Square payment ID to refund
            amount: Amount to refund in smallest currency unit (pence)
            currency: Currency code (default: GBP)
            reason: Optional reason for the refund
            idempotency_key: Optional idempotency key (uses payment_id if not provided)

        Returns:
            dict with success status, refund_id, and error details if failed
        """
        idempotency_key = idempotency_key or f"refund-{payment_id}-{uuid.uuid4()}"

        logger.info(f"Processing refund: payment_id={payment_id} amount={amount}")

        try:
            result = self.client.refunds.refund_payment(
                idempotency_key=idempotency_key,
                payment_id=payment_id,
                amount_money={"amount": amount, "currency": currency},
                reason=reason,
            )
            refund = result.refund

            logger.info(f"Refund successful: refund_id={refund.id} status={refund.status}")
            return {
                "success": True,
                "refund_id": refund.id,
                "status": refund.status,
                "amount": refund.amount_money.amount if refund.amount_money else 0,
                "currency": refund.amount_money.currency if refund.amount_money else "GBP",
            }

        except ApiError as e:
            errors = e.errors or []
            error_code = errors[0].code if errors else "REFUND_FAILED"
            error_detail = errors[0].detail if errors else ""
            logger.error(f"Refund failed: error_code={error_code} detail={error_detail}")
            return {
                "success": False,
                "error_code": error_code,
                "error_message": self._get_user_friendly_message(error_code, error_detail),
                "detail": str(errors),
            }

        except Exception as e:
            logger.error(f"Refund exception: {e}")
            return {
                "success": False,
                "error_code": "REFUND_EXCEPTION",
                "error_message": "An unexpected error occurred processing the refund.",
                "detail": str(e),
            }

    def list_payments(
        self,
        begin_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        List payments within a time range (for reconciliation).

        Args:
            begin_time: RFC 3339 timestamp for start of range
            end_time: RFC 3339 timestamp for end of range
            limit: Maximum number of payments to return

        Returns:
            List of payment dicts
        """
        try:
            result = self.client.payments.list(
                location_id=self.location_id,
                begin_time=begin_time,
                end_time=end_time,
                limit=limit,
            )
            payments = []
            for payment in result.payments or []:
                payments.append(
                    {
                        "id": payment.id,
                        "status": payment.status,
                        "amount_money": {
                            "amount": payment.amount_money.amount if payment.amount_money else 0,
                            "currency": payment.amount_money.currency
                            if payment.amount_money
                            else "GBP",
                        },
                        "created_at": payment.created_at,
                    }
                )
            return payments
        except ApiError as e:
            logger.warning(f"Failed to list payments: {e.errors}")
            return []
        except Exception as e:
            logger.error(f"Exception listing payments: {e}")
            return []


# Singleton instance
_payment_service: Optional[SquarePaymentService] = None


def get_payment_service() -> SquarePaymentService:
    """Get or create the Square payment service singleton."""
    global _payment_service
    if _payment_service is None:
        _payment_service = SquarePaymentService()
    return _payment_service


def reset_payment_service() -> None:
    """Reset the payment service singleton (useful for testing)."""
    global _payment_service
    _payment_service = None


def create_payment_service_for_tenant(
    tenant_settings: dict,
) -> SquarePaymentService | None:
    """Create a payment service using tenant-specific credentials.

    This factory function creates a new SquarePaymentService instance
    using credentials stored in the tenant's settings (encrypted).

    Args:
        tenant_settings: The tenant's settings dict containing Square config

    Returns:
        SquarePaymentService configured with tenant credentials, or None if not configured
    """
    from app.core.encryption import safe_decrypt

    square_config = tenant_settings.get("square", {})

    if not square_config.get("enabled", False):
        logger.debug("Square payments not enabled for tenant")
        return None

    # Decrypt credentials
    access_token = safe_decrypt(square_config.get("access_token_encrypted", ""))
    location_id = safe_decrypt(square_config.get("location_id_encrypted", ""))
    environment = square_config.get("environment", "sandbox")

    if not access_token or not location_id:
        logger.warning("Square credentials not configured for tenant")
        return None

    return SquarePaymentService(
        access_token=access_token,
        location_id=location_id,
        environment=environment,
    )
