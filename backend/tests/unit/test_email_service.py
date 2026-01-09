"""Tests for email service."""

from unittest.mock import MagicMock, patch


from app.services.email_service import EmailService, get_email_service


class TestEmailService:
    """Tests for EmailService class."""

    def test_init_with_api_key(self):
        """Test initialization when API key is configured."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="test@example.com",
                email_from_name="Test Sender",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                service = EmailService()

                assert service.api_key == "test-api-key"
                assert service.from_address == "test@example.com"
                assert service.from_name == "Test Sender"
                mock_resend.api_key = "test-api-key"

    def test_init_without_api_key(self):
        """Test initialization when API key is not configured."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="",
                email_from_address="test@example.com",
                email_from_name="Test Sender",
            )
            service = EmailService()

            assert service.api_key == ""
            assert not service.is_configured

    def test_is_configured_true(self):
        """Test is_configured returns True when API key exists."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="test@example.com",
                email_from_name="Test Sender",
            )
            service = EmailService()

            assert service.is_configured is True

    def test_is_configured_false(self):
        """Test is_configured returns False when API key is empty."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="",
                email_from_address="test@example.com",
                email_from_name="Test Sender",
            )
            service = EmailService()

            assert service.is_configured is False

    def test_is_configured_false_when_none(self):
        """Test is_configured returns False when API key is None."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key=None,
                email_from_address="test@example.com",
                email_from_name="Test Sender",
            )
            service = EmailService()

            assert service.is_configured is False


class TestSendOrderConfirmation:
    """Tests for send_order_confirmation method."""

    def test_send_order_confirmation_not_configured(self):
        """Test that email is not sent when service is not configured."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="",
                email_from_address="test@example.com",
                email_from_name="Test Sender",
            )
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
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

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
                mock_resend.Emails.send.assert_called_once()

                # Verify the email was sent with correct parameters
                call_args = mock_resend.Emails.send.call_args[0][0]
                assert call_args["to"] == ["customer@example.com"]
                assert call_args["from"] == "Mystmereforge <orders@mystmereforge.co.uk>"
                assert "Order Confirmation - MF-20251218-001" in call_args["subject"]
                assert "John Doe" in call_args["html"]
                assert "MF-20251218-001" in call_args["html"]
                assert "Rexy the T-Rex" in call_args["html"]
                assert "123 Test Street" in call_args["html"]
                assert "https://squareup.com/receipt/123" in call_args["html"]

    def test_send_order_confirmation_without_receipt_url(self):
        """Test order confirmation email without receipt URL."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                result = service.send_order_confirmation(
                    to_email="customer@example.com",
                    customer_name="Jane Doe",
                    order_number="MF-20251218-002",
                    order_items=[{"name": "Test Product", "quantity": 1, "price": 15.00}],
                    subtotal=15.00,
                    shipping_cost=3.99,
                    total=18.99,
                    shipping_address={
                        "address_line1": "456 Another St",
                        "city": "Manchester",
                        "postcode": "M1 1AA",
                        "country": "United Kingdom",
                    },
                    receipt_url=None,
                )

                assert result is True

                # Verify receipt section is not included when no URL
                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "View Payment Receipt" not in call_args["html"]

    def test_send_order_confirmation_minimal_address(self):
        """Test order confirmation with minimal address fields."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                result = service.send_order_confirmation(
                    to_email="customer@example.com",
                    customer_name="Test Customer",
                    order_number="MF-20251218-003",
                    order_items=[{"name": "Product", "quantity": 1, "price": 10.00}],
                    subtotal=10.00,
                    shipping_cost=0.00,
                    total=10.00,
                    shipping_address={
                        "address_line1": "Simple St",
                        "city": "City",
                        "postcode": "AB1 2CD",
                    },
                )

                assert result is True

    def test_send_order_confirmation_exception(self):
        """Test that exceptions are handled gracefully."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.side_effect = Exception("Resend API error")

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

    def test_send_order_confirmation_multiple_items(self):
        """Test email with multiple order items."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                result = service.send_order_confirmation(
                    to_email="bulk@example.com",
                    customer_name="Bulk Buyer",
                    order_number="MF-20251218-005",
                    order_items=[
                        {"name": "Item One", "quantity": 3, "price": 10.00},
                        {"name": "Item Two", "quantity": 1, "price": 25.00},
                        {"name": "Item Three", "quantity": 5, "price": 5.00},
                    ],
                    subtotal=80.00,
                    shipping_cost=5.99,
                    total=85.99,
                    shipping_address={
                        "address_line1": "Bulk Order Warehouse",
                        "city": "London",
                        "postcode": "E1 1AA",
                        "country": "United Kingdom",
                    },
                )

                assert result is True
                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "Item One" in call_args["html"]
                assert "Item Two" in call_args["html"]
                assert "Item Three" in call_args["html"]


class TestEmailServiceSingleton:
    """Tests for email service singleton."""

    def test_get_email_service_creates_singleton(self):
        """Test that get_email_service returns the same instance."""
        # Reset singleton
        import app.services.email_service as email_module

        email_module._email_service = None

        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-key",
                email_from_address="test@example.com",
                email_from_name="Test",
            )

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
            mock_settings.return_value = MagicMock(
                resend_api_key="test-key",
                email_from_address="test@example.com",
                email_from_name="Test",
            )

            service = get_email_service()

            assert isinstance(service, EmailService)

        # Reset singleton after test
        email_module._email_service = None


class TestEmailContent:
    """Tests for email content formatting."""

    def test_email_html_contains_order_details(self):
        """Test that email HTML contains all expected order details."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                service.send_order_confirmation(
                    to_email="test@example.com",
                    customer_name="Content Test",
                    order_number="MF-20251218-100",
                    order_items=[{"name": "Special Item", "quantity": 2, "price": 29.99}],
                    subtotal=59.98,
                    shipping_cost=4.50,
                    total=64.48,
                    shipping_address={
                        "address_line1": "Content Test Lane",
                        "city": "TestCity",
                        "postcode": "TC1 1TC",
                        "country": "TestCountry",
                    },
                    receipt_url="https://receipt.test/abc123",
                )

                html = mock_resend.Emails.send.call_args[0][0]["html"]

                # Check customer greeting
                assert "Content Test" in html

                # Check order number
                assert "MF-20251218-100" in html

                # Check item details
                assert "Special Item" in html

                # Check prices (formatted with currency symbol)
                assert "59.98" in html  # subtotal
                assert "4.50" in html  # shipping
                assert "64.48" in html  # total

                # Check address
                assert "Content Test Lane" in html
                assert "TestCity" in html
                assert "TC1 1TC" in html
                assert "TestCountry" in html

                # Check receipt link
                assert "https://receipt.test/abc123" in html
                assert "View Payment Receipt" in html

                # Check branding
                assert "Mystmereforge" in html
                assert "orders@mystmereforge.co.uk" in html

    def test_email_escapes_special_characters(self):
        """Test that email handles special characters in input."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                result = service.send_order_confirmation(
                    to_email="test@example.com",
                    customer_name="O'Brien & Sons",
                    order_number="MF-20251218-101",
                    order_items=[{"name": 'Product with "Quotes"', "quantity": 1, "price": 10.00}],
                    subtotal=10.00,
                    shipping_cost=0.00,
                    total=10.00,
                    shipping_address={
                        "address_line1": "123 O'Connell Street",
                        "city": "Dublin",
                        "postcode": "D01 ABC",
                        "country": "Ireland",
                    },
                )

                assert result is True


class TestSendRefundConfirmation:
    """Tests for send_refund_confirmation method."""

    def test_send_refund_confirmation_not_configured(self):
        """Test that refund email is not sent when service is not configured."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="",
                email_from_address="test@example.com",
                email_from_name="Test Sender",
            )
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
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

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
                mock_resend.Emails.send.assert_called_once()

                # Verify the email was sent with correct parameters
                call_args = mock_resend.Emails.send.call_args[0][0]
                assert call_args["to"] == ["customer@example.com"]
                assert call_args["from"] == "Mystmereforge <orders@mystmereforge.co.uk>"
                assert "Refund Confirmation - MF-20251219-001" in call_args["subject"]
                assert "John Doe" in call_args["html"]
                assert "MF-20251219-001" in call_args["html"]
                assert "50.00" in call_args["html"]
                assert "Customer requested refund" in call_args["html"]

    def test_send_refund_confirmation_without_reason(self):
        """Test refund confirmation email without reason."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                result = service.send_refund_confirmation(
                    to_email="customer@example.com",
                    customer_name="Jane Doe",
                    order_number="MF-20251219-002",
                    refund_amount=25.50,
                    reason=None,
                )

                assert result is True

                # Verify reason section is not included when no reason
                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "Reason:</strong>" not in call_args["html"]

    def test_send_refund_confirmation_gbp_currency(self):
        """Test refund email uses GBP symbol."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                service.send_refund_confirmation(
                    to_email="customer@example.com",
                    customer_name="Test Customer",
                    order_number="MF-20251219-003",
                    refund_amount=75.00,
                    currency="GBP",
                )

                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "£" in call_args["html"]
                assert "75.00" in call_args["html"]

    def test_send_refund_confirmation_usd_currency(self):
        """Test refund email uses USD symbol."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                service.send_refund_confirmation(
                    to_email="customer@example.com",
                    customer_name="Test Customer",
                    order_number="MF-20251219-004",
                    refund_amount=100.00,
                    currency="USD",
                )

                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "$" in call_args["html"]

    def test_send_refund_confirmation_eur_currency(self):
        """Test refund email uses EUR symbol."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                service.send_refund_confirmation(
                    to_email="customer@example.com",
                    customer_name="Test Customer",
                    order_number="MF-20251219-005",
                    refund_amount=50.00,
                    currency="EUR",
                )

                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "€" in call_args["html"]

    def test_send_refund_confirmation_unknown_currency(self):
        """Test refund email uses currency code for unknown currencies."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                service.send_refund_confirmation(
                    to_email="customer@example.com",
                    customer_name="Test Customer",
                    order_number="MF-20251219-006",
                    refund_amount=1000.00,
                    currency="JPY",
                )

                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "JPY" in call_args["html"]

    def test_send_refund_confirmation_exception(self):
        """Test that exceptions are handled gracefully."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.side_effect = Exception("Resend API error")

                service = EmailService()
                result = service.send_refund_confirmation(
                    to_email="customer@example.com",
                    customer_name="Test Customer",
                    order_number="MF-20251219-007",
                    refund_amount=25.00,
                )

                assert result is False

    def test_send_refund_confirmation_contains_branding(self):
        """Test refund email contains Mystmereforge branding."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                service.send_refund_confirmation(
                    to_email="customer@example.com",
                    customer_name="Test Customer",
                    order_number="MF-20251219-008",
                    refund_amount=30.00,
                )

                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "Mystmereforge" in call_args["html"]
                assert "mystmereforge.co.uk" in call_args["html"]
                assert "orders@mystmereforge.co.uk" in call_args["html"]

    def test_send_refund_confirmation_contains_bank_notice(self):
        """Test refund email contains bank processing time notice."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                service.send_refund_confirmation(
                    to_email="customer@example.com",
                    customer_name="Test Customer",
                    order_number="MF-20251219-009",
                    refund_amount=40.00,
                )

                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "5-10 business days" in call_args["html"]

    def test_send_refund_confirmation_default_currency(self):
        """Test refund email uses GBP as default currency."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                # Not specifying currency should default to GBP
                service.send_refund_confirmation(
                    to_email="customer@example.com",
                    customer_name="Test Customer",
                    order_number="MF-20251219-010",
                    refund_amount=55.00,
                )

                call_args = mock_resend.Emails.send.call_args[0][0]
                # Should use £ symbol (GBP default)
                assert "£" in call_args["html"]

    def test_send_refund_confirmation_special_characters_in_reason(self):
        """Test refund email handles special characters in reason."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                result = service.send_refund_confirmation(
                    to_email="customer@example.com",
                    customer_name="O'Brien & Partners",
                    order_number="MF-20251219-011",
                    refund_amount=60.00,
                    reason='Item didn\'t match "description" on site',
                )

                assert result is True
                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "O'Brien & Partners" in call_args["html"]

    def test_send_refund_confirmation_zero_amount(self):
        """Test refund email with zero amount."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                result = service.send_refund_confirmation(
                    to_email="customer@example.com",
                    customer_name="Test Customer",
                    order_number="MF-20251219-012",
                    refund_amount=0.00,
                )

                assert result is True
                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "0.00" in call_args["html"]

    def test_send_refund_confirmation_large_amount(self):
        """Test refund email with large amount."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmereforge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                result = service.send_refund_confirmation(
                    to_email="customer@example.com",
                    customer_name="Test Customer",
                    order_number="MF-20251219-013",
                    refund_amount=99999.99,
                )

                assert result is True
                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "99999.99" in call_args["html"]


class TestSendContactNotification:
    """Tests for send_contact_notification method."""

    def test_send_contact_notification_not_configured(self):
        """Test that contact email is not sent when service is not configured."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="",
                email_from_address="test@example.com",
                email_from_name="Test Sender",
            )
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
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmere Forge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

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
                assert mock_resend.Emails.send.call_count == 2

    def test_send_contact_notification_with_order_number(self):
        """Test contact notification with related order number."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmere Forge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                result = service.send_contact_notification(
                    name="Jane Doe",
                    email="jane@example.com",
                    subject="order",
                    message="Where is my order?",
                    reference="REF-20251229-002",
                    order_number="MF-20251220-001",
                )

                assert result is True
                # Check owner email contains order number
                first_call = mock_resend.Emails.send.call_args_list[0][0][0]
                assert "MF-20251220-001" in first_call["html"]

    def test_send_contact_notification_subject_labels(self):
        """Test contact notification maps subject codes to labels."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmere Forge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                service.send_contact_notification(
                    name="Test",
                    email="test@example.com",
                    subject="wholesale",
                    message="Interested in bulk orders.",
                    reference="REF-003",
                )

                first_call = mock_resend.Emails.send.call_args_list[0][0][0]
                assert "Wholesale/Events" in first_call["subject"]

    def test_send_contact_notification_exception(self):
        """Test that exceptions are handled gracefully."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmere Forge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.side_effect = Exception("Resend API error")

                service = EmailService()
                result = service.send_contact_notification(
                    name="Test",
                    email="test@example.com",
                    subject="feedback",
                    message="Great products!",
                    reference="REF-004",
                )

                assert result is False

    def test_send_contact_notification_sends_to_owner(self):
        """Test contact notification sends to hello@mystmereforge.co.uk."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmere Forge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                service.send_contact_notification(
                    name="Customer",
                    email="customer@example.com",
                    subject="other",
                    message="Question.",
                    reference="REF-005",
                )

                # First call should be to shop owner
                first_call = mock_resend.Emails.send.call_args_list[0][0][0]
                assert first_call["to"] == ["hello@mystmereforge.co.uk"]
                assert first_call["reply_to"] == "customer@example.com"

    def test_send_contact_notification_customer_confirmation(self):
        """Test contact notification sends confirmation to customer."""
        with patch("app.services.email_service.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                resend_api_key="test-api-key",
                email_from_address="orders@mystmereforge.co.uk",
                email_from_name="Mystmere Forge",
            )
            with patch("app.services.email_service.resend") as mock_resend:
                mock_resend.Emails.send.return_value = {"id": "email-123"}

                service = EmailService()
                service.send_contact_notification(
                    name="Customer",
                    email="customer@example.com",
                    subject="custom",
                    message="Custom request details.",
                    reference="REF-006",
                )

                # Second call should be to customer
                second_call = mock_resend.Emails.send.call_args_list[1][0][0]
                assert second_call["to"] == ["customer@example.com"]
                assert "REF-006" in second_call["html"]
                assert "We've received your message" in second_call["subject"]
