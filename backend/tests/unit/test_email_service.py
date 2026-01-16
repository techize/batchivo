"""Tests for email service."""

from unittest.mock import MagicMock, patch, Mock
import httpx


from app.services.email_service import EmailService, get_email_service


def get_mock_settings(**overrides):
    """Helper to create mock settings with shop branding defaults."""
    defaults = {
        "brevo_api_key": "test-api-key",
        "email_from_address": "orders@testshop.com",
        "email_from_name": "Test Shop",
        "frontend_base_url": "http://localhost:5173",
        "shop_name": "Test Shop",
        "shop_tagline": "Test Tagline",
        "shop_website_url": "https://testshop.com",
        "shop_orders_email": "orders@testshop.com",
        "shop_support_email": "support@testshop.com",
        "shop_social_handle": "@testshop",
        "shop_brand_color": "#6366f1",
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


class TestEmailService:
    """Tests for EmailService class."""

    def test_init_with_api_key(self):
        """Test initialization when API key is configured."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = get_mock_settings()
            service = EmailService()

            assert service.api_key == "test-api-key"
            assert service.from_address == "orders@testshop.com"
            assert service.from_name == "Test Shop"

    def test_init_without_api_key(self):
        """Test initialization when API key is not configured."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = get_mock_settings(brevo_api_key="")
            service = EmailService()

            assert service.api_key == ""
            assert not service.is_configured

    def test_is_configured_true(self):
        """Test is_configured returns True when API key exists."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = get_mock_settings()
            service = EmailService()

            assert service.is_configured is True

    def test_is_configured_false(self):
        """Test is_configured returns False when API key is empty."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = get_mock_settings(brevo_api_key="")
            service = EmailService()

            assert service.is_configured is False

    def test_is_configured_false_when_none(self):
        """Test is_configured returns False when API key is None."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = get_mock_settings(brevo_api_key=None)
            service = EmailService()

            assert service.is_configured is False


class TestSendOrderConfirmation:
    """Tests for send_order_confirmation method."""

    def test_send_order_confirmation_not_configured(self):
        """Test that email is not sent when service is not configured."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = get_mock_settings(brevo_api_key="")
            service = EmailService()

            result = service.send_order_confirmation(
                to_email="customer@example.com",
                customer_name="John Doe",
                order_number="MF-20251218-001",
                order_items=[{"name": "Product 1", "quantity": 2, "price": 19.99}],
                subtotal=39.98,
                shipping_cost=3.99,
                total=43.97,
                shipping_address={
                    "address_line1": "123 Test St",
                    "city": "London",
                    "postcode": "SW1A 1AA",
                    "country": "United Kingdom",
                },
            )

            assert result is False

    def test_send_order_confirmation_success(self):
        """Test successful order confirmation email."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = get_mock_settings()
            with patch("app.services.email_service.httpx.Client") as mock_client:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_client.return_value.__enter__ = Mock(return_value=mock_client.return_value)
                mock_client.return_value.__exit__ = Mock(return_value=False)
                mock_client.return_value.post.return_value = mock_response

                service = EmailService()
                result = service.send_order_confirmation(
                    to_email="customer@example.com",
                    customer_name="John Doe",
                    order_number="MF-20251218-001",
                    order_items=[
                        {"name": "Rexy the T-Rex", "quantity": 1, "price": 24.99},
                        {"name": "Steggy the Stegosaurus", "quantity": 2, "price": 19.99},
                    ],
                    subtotal=64.97,
                    shipping_cost=4.99,
                    total=69.96,
                    shipping_address={
                        "address_line1": "123 Test Street",
                        "address_line2": "Apt 4B",
                        "city": "London",
                        "county": "Greater London",
                        "postcode": "SW1A 1AA",
                        "country": "United Kingdom",
                    },
                    receipt_url="https://squareup.com/receipt/123",
                )

                assert result is True
                mock_client.return_value.post.assert_called_once()

    def test_send_order_confirmation_exception(self):
        """Test that exceptions are handled gracefully."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = get_mock_settings()
            with patch("app.services.email_service.httpx.Client") as mock_client:
                mock_client.return_value.__enter__ = Mock(return_value=mock_client.return_value)
                mock_client.return_value.__exit__ = Mock(return_value=False)
                mock_client.return_value.post.side_effect = Exception("Brevo API error")

                service = EmailService()
                result = service.send_order_confirmation(
                    to_email="customer@example.com",
                    customer_name="Test Customer",
                    order_number="MF-20251218-004",
                    order_items=[{"name": "Product", "quantity": 1, "price": 10.00}],
                    subtotal=10.00,
                    shipping_cost=2.99,
                    total=12.99,
                    shipping_address={
                        "address_line1": "Error St",
                        "city": "ErrorCity",
                        "postcode": "ER1 1OR",
                        "country": "United Kingdom",
                    },
                )

                assert result is False


class TestEmailServiceSingleton:
    """Tests for email service singleton."""

    def test_get_email_service_creates_singleton(self):
        """Test that get_email_service returns the same instance."""
        # Reset singleton
        import app.services.email_service as email_module

        email_module._email_service = None

        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = get_mock_settings()

            service1 = get_email_service()
            service2 = get_email_service()

            assert service1 is service2

        # Reset singleton after test
        email_module._email_service = None

    def test_get_email_service_returns_email_service(self):
        """Test that get_email_service returns an EmailService instance."""
        import app.services.email_service as email_module

        email_module._email_service = None

        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = get_mock_settings()

            service = get_email_service()

            assert isinstance(service, EmailService)

        # Reset singleton after test
        email_module._email_service = None


class TestSendRefundConfirmation:
    """Tests for send_refund_confirmation method."""

    def test_send_refund_confirmation_not_configured(self):
        """Test that refund email is not sent when service is not configured."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = get_mock_settings(brevo_api_key="")
            service = EmailService()

            result = service.send_refund_confirmation(
                to_email="customer@example.com",
                customer_name="John Doe",
                order_number="MF-20251219-001",
                refund_amount=50.00,
            )

            assert result is False

    def test_send_refund_confirmation_success(self):
        """Test successful refund confirmation email."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = get_mock_settings()
            with patch("app.services.email_service.httpx.Client") as mock_client:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_client.return_value.__enter__ = Mock(return_value=mock_client.return_value)
                mock_client.return_value.__exit__ = Mock(return_value=False)
                mock_client.return_value.post.return_value = mock_response

                service = EmailService()
                result = service.send_refund_confirmation(
                    to_email="customer@example.com",
                    customer_name="John Doe",
                    order_number="MF-20251219-001",
                    refund_amount=50.00,
                    currency="GBP",
                    reason="Customer requested refund",
                )

                assert result is True
                mock_client.return_value.post.assert_called_once()


class TestSendContactNotification:
    """Tests for send_contact_notification method."""

    def test_send_contact_notification_not_configured(self):
        """Test that contact email is not sent when service is not configured."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = get_mock_settings(brevo_api_key="")
            service = EmailService()

            result = service.send_contact_notification(
                name="John Doe",
                email="john@example.com",
                subject="custom",
                message="I would like a custom dragon.",
                reference="REF-001",
            )

            assert result is False

    def test_send_contact_notification_success(self):
        """Test successful contact notification email to owner and customer."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = get_mock_settings()
            with patch("app.services.email_service.httpx.Client") as mock_client:
                mock_response = Mock()
                mock_response.raise_for_status = Mock()
                mock_client.return_value.__enter__ = Mock(return_value=mock_client.return_value)
                mock_client.return_value.__exit__ = Mock(return_value=False)
                mock_client.return_value.post.return_value = mock_response

                service = EmailService()
                result = service.send_contact_notification(
                    name="John Doe",
                    email="john@example.com",
                    subject="custom",
                    message="I would like a custom dragon in blue.",
                    reference="REF-20251229-001",
                )

                assert result is True
                # Should send 2 emails: one to owner, one to customer
                assert mock_client.return_value.post.call_count == 2
