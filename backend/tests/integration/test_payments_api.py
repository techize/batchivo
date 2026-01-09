"""Integration tests for payments API endpoints."""

from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import app
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.sales_channel import SalesChannel
from app.models.tenant import Tenant
from app.schemas.payment import PaymentError, PaymentResponse
from app.services.cart import CartService, get_cart_service
from app.services.checkout_session import CheckoutSessionService, get_checkout_session_service
from app.services.stock_reservation import StockReservationService, get_stock_reservation_service
from tests.utils.mock_redis import MockRedis


# ============================================
# Redis Mock Fixtures
# ============================================


@pytest.fixture
def fake_redis():
    """Create a fake Redis client for testing."""
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def mock_cart_service(fake_redis):
    """Create a cart service with fake Redis."""
    return CartService(redis_client=fake_redis)


@pytest.fixture
def mock_checkout_service(fake_redis):
    """Create a checkout session service with fake Redis."""
    return CheckoutSessionService(redis_client=fake_redis)


@pytest.fixture
def mock_reservation_redis():
    """Create a MockRedis that supports Lua scripts for stock reservation."""
    return MockRedis()


@pytest.fixture
def mock_reservation_service(mock_reservation_redis):
    """Create a stock reservation service with MockRedis (supports Lua scripts)."""
    return StockReservationService(redis_client=mock_reservation_redis)


@pytest.fixture(autouse=True)
def override_redis_services(mock_cart_service, mock_checkout_service, mock_reservation_service):
    """Override Redis-based services with mocks for all tests."""
    app.dependency_overrides[get_cart_service] = lambda: mock_cart_service
    app.dependency_overrides[get_checkout_session_service] = lambda: mock_checkout_service
    app.dependency_overrides[get_stock_reservation_service] = lambda: mock_reservation_service
    yield
    # Clean up overrides
    app.dependency_overrides.pop(get_cart_service, None)
    app.dependency_overrides.pop(get_checkout_session_service, None)
    app.dependency_overrides.pop(get_stock_reservation_service, None)


@pytest_asyncio.fixture(scope="function")
async def online_shop_channel(db_session: AsyncSession, test_tenant: Tenant) -> SalesChannel:
    """Create an online_shop sales channel for shop context resolution."""
    channel = SalesChannel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Test Online Shop",
        platform_type="online_shop",
        is_active=True,
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    return channel


@pytest_asyncio.fixture(scope="function")
async def payments_client(
    db_session: AsyncSession,
    seed_material_types,
    test_tenant: Tenant,
    online_shop_channel: SalesChannel,
) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client for payments with ShopContext."""
    from app.auth.dependencies import get_shop_sales_channel, get_shop_tenant

    async def override_get_db():
        yield db_session

    async def override_get_shop_tenant():
        return test_tenant

    async def override_get_shop_sales_channel():
        return (test_tenant, online_shop_channel)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_shop_tenant] = override_get_shop_tenant
    app.dependency_overrides[get_shop_sales_channel] = override_get_shop_sales_channel
    app.state.limiter.enabled = False

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.state.limiter.enabled = True
    # Only remove the overrides we added, not all overrides (preserves Redis mocks)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_shop_tenant, None)
    app.dependency_overrides.pop(get_shop_sales_channel, None)


@pytest_asyncio.fixture(scope="function")
async def mystmereforge_channel(db_session: AsyncSession, test_tenant: Tenant) -> SalesChannel:
    """Create the Mystmereforge sales channel."""
    channel = SalesChannel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Mystmereforge",
        platform_type="shopify",
        is_active=True,
    )
    db_session.add(channel)
    await db_session.commit()
    await db_session.refresh(channel)
    return channel


@pytest_asyncio.fixture(scope="function")
async def shop_product(db_session: AsyncSession, test_tenant: Tenant) -> Product:
    """Create a shop-visible product."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="SHOP-PROD-001",
        name="Shop Test Product",
        description="A product for shop testing",
        units_in_stock=100,
        is_active=True,
        shop_visible=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


class TestGetPaymentConfig:
    """Tests for GET /api/v1/payments/config endpoint."""

    async def test_get_config_enabled(self, payments_client: AsyncClient):
        """Test config returns enabled when Square is configured."""
        with patch("app.api.v1.payments.settings") as mock_settings:
            mock_settings.square_access_token = "test-token"
            mock_settings.square_location_id = "test-location"
            mock_settings.square_environment = "sandbox"
            mock_settings.square_app_id = "test-app-id"

            response = await payments_client.get("/api/v1/payments/config")

            assert response.status_code == 200
            data = response.json()
            assert data["enabled"] is True
            assert data["environment"] == "sandbox"

    async def test_get_config_disabled_no_token(self, payments_client: AsyncClient):
        """Test config returns disabled when no token."""
        with patch("app.api.v1.payments.settings") as mock_settings:
            mock_settings.square_access_token = ""
            mock_settings.square_location_id = "test-location"
            mock_settings.square_environment = "sandbox"

            response = await payments_client.get("/api/v1/payments/config")

            assert response.status_code == 200
            data = response.json()
            assert data["enabled"] is False

    async def test_get_config_disabled_no_location(self, payments_client: AsyncClient):
        """Test config returns disabled when no location ID."""
        with patch("app.api.v1.payments.settings") as mock_settings:
            mock_settings.square_access_token = "test-token"
            mock_settings.square_location_id = ""
            mock_settings.square_environment = "production"

            response = await payments_client.get("/api/v1/payments/config")

            assert response.status_code == 200
            data = response.json()
            assert data["enabled"] is False
            assert data["environment"] == "production"


class TestProcessPayment:
    """Tests for POST /api/v1/payments/process endpoint."""

    def _create_payment_body(
        self,
        product_id: str,
        amount: int = 2999,
        item_price: int = 2500,
        shipping_cost: int = 499,
    ) -> dict:
        """Create a payment request body."""
        return {
            "payment_token": "cnon:card-nonce-ok",
            "amount": amount,
            "currency": "GBP",
            "customer": {
                "email": "customer@example.com",
                "phone": "+44123456789",
            },
            "shipping_address": {
                "first_name": "John",
                "last_name": "Doe",
                "address_line1": "123 Test Street",
                "address_line2": "Apt 4B",
                "city": "London",
                "county": "Greater London",
                "postcode": "SW1A 1AA",
                "country": "GB",
            },
            "shipping_method": "standard",
            "shipping_cost": shipping_cost,
            "items": [
                {
                    "product_id": product_id,
                    "name": "Test Product",
                    "quantity": 1,
                    "price": item_price,
                }
            ],
        }

    async def test_process_payment_not_configured(self, payments_client: AsyncClient):
        """Test payment fails when Square not configured."""
        with patch("app.api.v1.payments.settings") as mock_settings:
            mock_settings.square_access_token = ""
            mock_settings.square_location_id = ""

            response = await payments_client.post(
                "/api/v1/payments/process",
                json=self._create_payment_body(str(uuid4())),
            )

            assert response.status_code == 503
            assert "not configured" in response.json()["detail"]

    async def test_process_payment_amount_mismatch(
        self, payments_client: AsyncClient, shop_product: Product
    ):
        """Test payment fails when amount doesn't match items + shipping."""
        with patch("app.api.v1.payments.settings") as mock_settings:
            mock_settings.square_access_token = "test-token"
            mock_settings.square_location_id = "test-location"

            body = self._create_payment_body(str(shop_product.id))
            body["amount"] = 9999  # Wrong amount

            response = await payments_client.post(
                "/api/v1/payments/process",
                json=body,
            )

            assert response.status_code == 400
            assert "Amount mismatch" in response.json()["detail"]

    async def test_process_payment_success(
        self,
        payments_client: AsyncClient,
        shop_product: Product,
        mystmereforge_channel: SalesChannel,
        db_session: AsyncSession,
    ):
        """Test successful payment processing creates order."""
        with patch("app.api.v1.payments.settings") as mock_settings:
            mock_settings.square_access_token = "test-token"
            mock_settings.square_location_id = "test-location"

            with patch("app.api.v1.payments.get_payment_service") as mock_get_service:
                mock_service = MagicMock()
                mock_service.process_payment.return_value = PaymentResponse(
                    success=True,
                    order_id="MF-TEMP123",
                    payment_id="sq_payment_123",
                    amount=2999,
                    currency="GBP",
                    status="COMPLETED",
                    receipt_url="https://squareup.com/receipt/test",
                    created_at=datetime.now(timezone.utc),
                )
                mock_get_service.return_value = mock_service

                with patch("app.api.v1.payments.get_email_service") as mock_get_email:
                    mock_email = MagicMock()
                    mock_email.send_order_confirmation.return_value = True
                    mock_get_email.return_value = mock_email

                    body = self._create_payment_body(str(shop_product.id))

                    response = await payments_client.post(
                        "/api/v1/payments/process",
                        json=body,
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True
                    assert data["payment_id"] == "sq_payment_123"
                    assert data["status"] == "COMPLETED"
                    # Order number format is {TENANT_PREFIX}-{DATE}-{SEQUENCE}
                    assert "-" in data["order_id"]
                    assert len(data["order_id"]) > 10

                    # Verify order was created in database
                    result = await db_session.execute(
                        select(Order).where(Order.payment_id == "sq_payment_123")
                    )
                    order = result.scalar_one_or_none()
                    assert order is not None
                    assert order.customer_email == "customer@example.com"
                    assert order.status == OrderStatus.PENDING
                    assert order.payment_status == "COMPLETED"

                    # Verify email was sent
                    mock_email.send_order_confirmation.assert_called_once()

    async def test_process_payment_card_declined(
        self,
        payments_client: AsyncClient,
        shop_product: Product,
        mystmereforge_channel: SalesChannel,
    ):
        """Test payment failure returns 402."""
        with patch("app.api.v1.payments.settings") as mock_settings:
            mock_settings.square_access_token = "test-token"
            mock_settings.square_location_id = "test-location"

            with patch("app.api.v1.payments.get_payment_service") as mock_get_service:
                mock_service = MagicMock()
                mock_service.process_payment.return_value = PaymentError(
                    success=False,
                    error_code="CARD_DECLINED",
                    error_message="Card was declined",
                    detail="Insufficient funds",
                )
                mock_get_service.return_value = mock_service

                body = self._create_payment_body(str(shop_product.id))

                response = await payments_client.post(
                    "/api/v1/payments/process",
                    json=body,
                )

                assert response.status_code == 402
                detail = response.json()["detail"]
                assert detail["error_code"] == "CARD_DECLINED"

    async def test_process_payment_creates_order_items(
        self,
        payments_client: AsyncClient,
        shop_product: Product,
        mystmereforge_channel: SalesChannel,
        db_session: AsyncSession,
    ):
        """Test order items are created correctly."""
        with patch("app.api.v1.payments.settings") as mock_settings:
            mock_settings.square_access_token = "test-token"
            mock_settings.square_location_id = "test-location"

            with patch("app.api.v1.payments.get_payment_service") as mock_get_service:
                mock_service = MagicMock()
                mock_service.process_payment.return_value = PaymentResponse(
                    success=True,
                    order_id="MF-TEST",
                    payment_id="sq_items_test",
                    amount=5498,
                    currency="GBP",
                    status="COMPLETED",
                    created_at=datetime.now(timezone.utc),
                )
                mock_get_service.return_value = mock_service

                with patch("app.api.v1.payments.get_email_service") as mock_get_email:
                    mock_email = MagicMock()
                    mock_email.send_order_confirmation.return_value = True
                    mock_get_email.return_value = mock_email

                    body = {
                        "payment_token": "cnon:card-nonce-ok",
                        "amount": 5498,
                        "currency": "GBP",
                        "customer": {"email": "items@example.com"},
                        "shipping_address": {
                            "first_name": "Item",
                            "last_name": "Test",
                            "address_line1": "Items St",
                            "city": "London",
                            "postcode": "E1 1AA",
                            "country": "GB",
                        },
                        "shipping_method": "standard",
                        "shipping_cost": 499,
                        "items": [
                            {
                                "product_id": str(shop_product.id),
                                "name": "Product A",
                                "quantity": 2,
                                "price": 1500,
                            },
                            {
                                "product_id": str(uuid4()),  # Non-existent product
                                "name": "Product B",
                                "quantity": 1,
                                "price": 1999,
                            },
                        ],
                    }

                    response = await payments_client.post(
                        "/api/v1/payments/process",
                        json=body,
                    )

                    assert response.status_code == 200

                    # Verify order items
                    result = await db_session.execute(
                        select(Order).where(Order.payment_id == "sq_items_test")
                    )
                    order = result.scalar_one()

                    items_result = await db_session.execute(
                        select(OrderItem).where(OrderItem.order_id == order.id)
                    )
                    items = items_result.scalars().all()

                    assert len(items) == 2

                    # Check first item (existing product)
                    item_a = next(i for i in items if i.product_name == "Product A")
                    assert item_a.product_id == shop_product.id
                    assert item_a.quantity == 2
                    assert float(item_a.unit_price) == 15.00

                    # Check second item (non-existent product)
                    item_b = next(i for i in items if i.product_name == "Product B")
                    assert item_b.product_id is None
                    assert item_b.quantity == 1

    async def test_process_payment_order_number_sequence(
        self,
        payments_client: AsyncClient,
        shop_product: Product,
        mystmereforge_channel: SalesChannel,
        db_session: AsyncSession,
    ):
        """Test order numbers are sequential for the same day."""
        with patch("app.api.v1.payments.settings") as mock_settings:
            mock_settings.square_access_token = "test-token"
            mock_settings.square_location_id = "test-location"

            order_numbers = []
            for i in range(3):
                with patch("app.api.v1.payments.get_payment_service") as mock_get_service:
                    mock_service = MagicMock()
                    mock_service.process_payment.return_value = PaymentResponse(
                        success=True,
                        order_id="MF-TEMP",
                        payment_id=f"sq_seq_test_{i}",
                        amount=2999,
                        currency="GBP",
                        status="COMPLETED",
                        created_at=datetime.now(timezone.utc),
                    )
                    mock_get_service.return_value = mock_service

                    with patch("app.api.v1.payments.get_email_service") as mock_get_email:
                        mock_email = MagicMock()
                        mock_email.send_order_confirmation.return_value = True
                        mock_get_email.return_value = mock_email

                        body = self._create_payment_body(str(shop_product.id))

                        response = await payments_client.post(
                            "/api/v1/payments/process",
                            json=body,
                        )

                        assert response.status_code == 200
                        order_numbers.append(response.json()["order_id"])

            # Verify sequential numbering
            assert order_numbers[0].endswith("-001")
            assert order_numbers[1].endswith("-002")
            assert order_numbers[2].endswith("-003")

    async def test_process_payment_missing_sales_channel_still_succeeds(
        self, payments_client: AsyncClient, shop_product: Product
    ):
        """Test payment succeeds even when order creation fails (no sales channel).

        The payment is processed first, and if order creation fails, the error is
        logged but payment success is still returned (can be reconciled from Square).
        """
        with patch("app.api.v1.payments.settings") as mock_settings:
            mock_settings.square_access_token = "test-token"
            mock_settings.square_location_id = "test-location"

            with patch("app.api.v1.payments.get_payment_service") as mock_get_service:
                mock_service = MagicMock()
                mock_service.process_payment.return_value = PaymentResponse(
                    success=True,
                    order_id="MF-TEMP",
                    payment_id="sq_no_channel",
                    amount=2999,
                    currency="GBP",
                    status="COMPLETED",
                    created_at=datetime.now(timezone.utc),
                )
                mock_get_service.return_value = mock_service

                body = self._create_payment_body(str(shop_product.id))

                response = await payments_client.post(
                    "/api/v1/payments/process",
                    json=body,
                )

                # Payment still succeeds - order creation failure is logged only
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["payment_id"] == "sq_no_channel"

    async def test_process_payment_validation_errors(self, payments_client: AsyncClient):
        """Test payment validation for required fields."""
        with patch("app.api.v1.payments.settings") as mock_settings:
            mock_settings.square_access_token = "test-token"
            mock_settings.square_location_id = "test-location"

            # Missing payment_token
            response = await payments_client.post(
                "/api/v1/payments/process",
                json={
                    "amount": 1000,
                    "currency": "GBP",
                    "customer": {"email": "test@example.com"},
                    "shipping_address": {
                        "first_name": "Test",
                        "last_name": "User",
                        "address_line1": "123 St",
                        "city": "City",
                        "postcode": "AB1 2CD",
                        "country": "GB",
                    },
                    "shipping_method": "standard",
                    "shipping_cost": 0,
                    "items": [],
                },
            )

            assert response.status_code == 422


class TestGetPaymentStatus:
    """Tests for GET /api/v1/payments/status/{payment_id} endpoint."""

    async def test_get_status_not_configured(self, payments_client: AsyncClient):
        """Test status fails when Square not configured."""
        with patch("app.api.v1.payments.settings") as mock_settings:
            mock_settings.square_access_token = ""

            response = await payments_client.get("/api/v1/payments/status/payment_123")

            assert response.status_code == 503
            assert "not configured" in response.json()["detail"]

    async def test_get_status_success(self, payments_client: AsyncClient):
        """Test successful payment status retrieval."""
        with patch("app.api.v1.payments.settings") as mock_settings:
            mock_settings.square_access_token = "test-token"

            with patch("app.api.v1.payments.get_payment_service") as mock_get_service:
                mock_service = MagicMock()
                mock_service.get_payment.return_value = {
                    "id": "sq_pay_123",
                    "status": "COMPLETED",
                    "amount_money": {"amount": 5000, "currency": "GBP"},
                    "receipt_url": "https://squareup.com/receipt/xyz",
                }
                mock_get_service.return_value = mock_service

                response = await payments_client.get("/api/v1/payments/status/sq_pay_123")

                assert response.status_code == 200
                data = response.json()
                assert data["payment_id"] == "sq_pay_123"
                assert data["status"] == "COMPLETED"
                assert data["amount"] == 5000
                assert data["currency"] == "GBP"
                assert data["receipt_url"] == "https://squareup.com/receipt/xyz"

    async def test_get_status_not_found(self, payments_client: AsyncClient):
        """Test payment not found returns 404."""
        with patch("app.api.v1.payments.settings") as mock_settings:
            mock_settings.square_access_token = "test-token"

            with patch("app.api.v1.payments.get_payment_service") as mock_get_service:
                mock_service = MagicMock()
                mock_service.get_payment.return_value = None
                mock_get_service.return_value = mock_service

                response = await payments_client.get("/api/v1/payments/status/nonexistent_id")

                assert response.status_code == 404
                assert "not found" in response.json()["detail"]
