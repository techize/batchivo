"""Tests for discount codes API."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.discount import DiscountCode, DiscountType, DiscountUsage
from app.models.order import Order


# ============================================
# Fixtures
# ============================================


@pytest.fixture
async def test_discount_code(db_session: AsyncSession, test_tenant):
    """Create a test discount code."""
    discount = DiscountCode(
        tenant_id=test_tenant.id,
        code="TEST10",
        name="Test 10% Off",
        description="Test discount code",
        discount_type=DiscountType.PERCENTAGE.value,
        amount=Decimal("10.00"),
        min_order_amount=Decimal("20.00"),
        max_discount_amount=Decimal("50.00"),
        max_uses=100,
        max_uses_per_customer=2,
        current_uses=0,
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_to=datetime.now(timezone.utc) + timedelta(days=30),
        is_active=True,
    )
    db_session.add(discount)
    await db_session.commit()
    await db_session.refresh(discount)
    return discount


@pytest.fixture
async def test_fixed_discount(db_session: AsyncSession, test_tenant):
    """Create a test fixed amount discount code."""
    discount = DiscountCode(
        tenant_id=test_tenant.id,
        code="FLAT5",
        name="£5 Off",
        description="Fixed £5 discount",
        discount_type=DiscountType.FIXED_AMOUNT.value,
        amount=Decimal("5.00"),
        min_order_amount=None,
        max_discount_amount=None,
        max_uses=None,
        max_uses_per_customer=None,
        current_uses=0,
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        valid_to=None,  # No expiry
        is_active=True,
    )
    db_session.add(discount)
    await db_session.commit()
    await db_session.refresh(discount)
    return discount


@pytest.fixture
async def expired_discount(db_session: AsyncSession, test_tenant):
    """Create an expired discount code."""
    discount = DiscountCode(
        tenant_id=test_tenant.id,
        code="EXPIRED",
        name="Expired Discount",
        discount_type=DiscountType.PERCENTAGE.value,
        amount=Decimal("20.00"),
        valid_from=datetime.now(timezone.utc) - timedelta(days=30),
        valid_to=datetime.now(timezone.utc) - timedelta(days=1),  # Expired
        is_active=True,
    )
    db_session.add(discount)
    await db_session.commit()
    await db_session.refresh(discount)
    return discount


@pytest.fixture
async def inactive_discount(db_session: AsyncSession, test_tenant):
    """Create an inactive discount code."""
    discount = DiscountCode(
        tenant_id=test_tenant.id,
        code="INACTIVE",
        name="Inactive Discount",
        discount_type=DiscountType.PERCENTAGE.value,
        amount=Decimal("15.00"),
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        is_active=False,  # Inactive
    )
    db_session.add(discount)
    await db_session.commit()
    await db_session.refresh(discount)
    return discount


# ============================================
# List Discount Codes Tests
# ============================================


@pytest.mark.asyncio
async def test_list_discount_codes(client: AsyncClient, test_discount_code, test_fixed_discount):
    """Test listing discount codes."""
    response = await client.get("/api/v1/discounts")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 2

    codes = [item["code"] for item in data["items"]]
    assert "TEST10" in codes
    assert "FLAT5" in codes


@pytest.mark.asyncio
async def test_list_discount_codes_search(client: AsyncClient, test_discount_code):
    """Test searching discount codes."""
    response = await client.get("/api/v1/discounts?search=TEST")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] >= 1
    assert any(item["code"] == "TEST10" for item in data["items"])


@pytest.mark.asyncio
async def test_list_discount_codes_filter_active(
    client: AsyncClient, test_discount_code, inactive_discount
):
    """Test filtering by active status."""
    # Active only
    response = await client.get("/api/v1/discounts?is_active=true")
    assert response.status_code == 200
    data = response.json()
    assert all(item["is_active"] for item in data["items"])

    # Inactive only
    response = await client.get("/api/v1/discounts?is_active=false")
    assert response.status_code == 200
    data = response.json()
    assert all(not item["is_active"] for item in data["items"])


# ============================================
# Get Single Discount Code Tests
# ============================================


@pytest.mark.asyncio
async def test_get_discount_code(client: AsyncClient, test_discount_code):
    """Test getting a single discount code."""
    response = await client.get(f"/api/v1/discounts/{test_discount_code.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["code"] == "TEST10"
    assert data["name"] == "Test 10% Off"
    assert data["discount_type"] == "percentage"
    assert Decimal(data["amount"]) == Decimal("10.00")


@pytest.mark.asyncio
async def test_get_discount_code_not_found(client: AsyncClient):
    """Test getting non-existent discount code."""
    response = await client.get(f"/api/v1/discounts/{uuid4()}")
    assert response.status_code == 404


# ============================================
# Create Discount Code Tests
# ============================================


@pytest.mark.asyncio
async def test_create_discount_code_percentage(client: AsyncClient):
    """Test creating a percentage discount code."""
    response = await client.post(
        "/api/v1/discounts",
        json={
            "code": "NEW20",
            "name": "20% New Customer",
            "description": "Welcome discount",
            "discount_type": "percentage",
            "amount": "20.00",
            "min_order_amount": "30.00",
            "valid_from": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
        },
    )
    assert response.status_code == 201

    data = response.json()
    assert data["code"] == "NEW20"
    assert data["discount_type"] == "percentage"
    assert Decimal(data["amount"]) == Decimal("20.00")


@pytest.mark.asyncio
async def test_create_discount_code_fixed(client: AsyncClient):
    """Test creating a fixed amount discount code."""
    response = await client.post(
        "/api/v1/discounts",
        json={
            "code": "FIXED10",
            "name": "£10 Off",
            "discount_type": "fixed_amount",
            "amount": "10.00",
            "valid_from": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 201

    data = response.json()
    assert data["code"] == "FIXED10"
    assert data["discount_type"] == "fixed_amount"


@pytest.mark.asyncio
async def test_create_discount_code_duplicate(client: AsyncClient, test_discount_code):
    """Test creating duplicate discount code fails."""
    response = await client.post(
        "/api/v1/discounts",
        json={
            "code": "TEST10",  # Same as test_discount_code
            "name": "Duplicate",
            "discount_type": "percentage",
            "amount": "5.00",
            "valid_from": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_discount_code_percentage_over_100(client: AsyncClient):
    """Test that percentage discount cannot exceed 100%."""
    response = await client.post(
        "/api/v1/discounts",
        json={
            "code": "INVALID",
            "name": "Invalid Percentage",
            "discount_type": "percentage",
            "amount": "150.00",  # Invalid
            "valid_from": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 400
    assert "100%" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_discount_code_case_insensitive(client: AsyncClient):
    """Test that codes are converted to uppercase."""
    response = await client.post(
        "/api/v1/discounts",
        json={
            "code": "lowercase",
            "name": "Lowercase Test",
            "discount_type": "percentage",
            "amount": "5.00",
            "valid_from": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 201
    assert response.json()["code"] == "LOWERCASE"


# ============================================
# Update Discount Code Tests
# ============================================


@pytest.mark.asyncio
async def test_update_discount_code(client: AsyncClient, test_discount_code):
    """Test updating a discount code."""
    response = await client.patch(
        f"/api/v1/discounts/{test_discount_code.id}",
        json={
            "name": "Updated Name",
            "amount": "15.00",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Updated Name"
    assert Decimal(data["amount"]) == Decimal("15.00")


@pytest.mark.asyncio
async def test_update_discount_code_deactivate(client: AsyncClient, test_discount_code):
    """Test deactivating a discount code."""
    response = await client.patch(
        f"/api/v1/discounts/{test_discount_code.id}",
        json={"is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


# ============================================
# Delete Discount Code Tests
# ============================================


@pytest.mark.asyncio
async def test_delete_discount_code(client: AsyncClient, db_session: AsyncSession, test_tenant):
    """Test deleting a discount code."""
    # Create a code to delete
    discount = DiscountCode(
        tenant_id=test_tenant.id,
        code="TODELETE",
        name="To Delete",
        discount_type=DiscountType.PERCENTAGE.value,
        amount=Decimal("5.00"),
        valid_from=datetime.now(timezone.utc),
        is_active=True,
    )
    db_session.add(discount)
    await db_session.commit()
    await db_session.refresh(discount)

    response = await client.delete(f"/api/v1/discounts/{discount.id}")
    assert response.status_code == 204

    # Verify deleted
    result = await db_session.execute(select(DiscountCode).where(DiscountCode.id == discount.id))
    assert result.scalar_one_or_none() is None


# ============================================
# Validate Discount Code Tests
# ============================================


@pytest.mark.asyncio
async def test_validate_discount_code_success(client: AsyncClient, test_discount_code):
    """Test validating a valid discount code."""
    response = await client.post(
        "/api/v1/discounts/validate",
        json={
            "code": "TEST10",
            "subtotal": "50.00",
            "customer_email": "test@example.com",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["valid"] is True
    assert data["code"] == "TEST10"
    assert data["discount_type"] == "percentage"
    # 10% of £50 = £5.00
    assert Decimal(data["discount_amount"]) == Decimal("5.00")


@pytest.mark.asyncio
async def test_validate_discount_code_fixed_amount(client: AsyncClient, test_fixed_discount):
    """Test validating a fixed amount discount code."""
    response = await client.post(
        "/api/v1/discounts/validate",
        json={
            "code": "FLAT5",
            "subtotal": "30.00",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["valid"] is True
    assert Decimal(data["discount_amount"]) == Decimal("5.00")


@pytest.mark.asyncio
async def test_validate_discount_code_invalid(client: AsyncClient):
    """Test validating an invalid discount code."""
    response = await client.post(
        "/api/v1/discounts/validate",
        json={
            "code": "NOTEXIST",
            "subtotal": "50.00",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["valid"] is False
    assert "Invalid discount code" in data["message"]


@pytest.mark.asyncio
async def test_validate_discount_code_expired(client: AsyncClient, expired_discount):
    """Test validating an expired discount code."""
    response = await client.post(
        "/api/v1/discounts/validate",
        json={
            "code": "EXPIRED",
            "subtotal": "50.00",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["valid"] is False
    assert "expired" in data["message"]


@pytest.mark.asyncio
async def test_validate_discount_code_inactive(client: AsyncClient, inactive_discount):
    """Test validating an inactive discount code."""
    response = await client.post(
        "/api/v1/discounts/validate",
        json={
            "code": "INACTIVE",
            "subtotal": "50.00",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["valid"] is False
    assert "no longer active" in data["message"]


@pytest.mark.asyncio
async def test_validate_discount_code_min_order_not_met(client: AsyncClient, test_discount_code):
    """Test validating with subtotal below minimum."""
    # test_discount_code has min_order_amount = £20
    response = await client.post(
        "/api/v1/discounts/validate",
        json={
            "code": "TEST10",
            "subtotal": "15.00",  # Below minimum
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["valid"] is False
    assert "Minimum order amount" in data["message"]


@pytest.mark.asyncio
async def test_validate_discount_code_max_discount_cap(client: AsyncClient, test_discount_code):
    """Test that percentage discount is capped by max_discount_amount."""
    # test_discount_code is 10% with max_discount_amount = £50
    # On a £1000 order, 10% would be £100, but capped at £50
    response = await client.post(
        "/api/v1/discounts/validate",
        json={
            "code": "TEST10",
            "subtotal": "1000.00",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["valid"] is True
    # Should be capped at £50
    assert Decimal(data["discount_amount"]) == Decimal("50.00")


@pytest.mark.asyncio
async def test_validate_discount_code_case_insensitive(client: AsyncClient, test_discount_code):
    """Test that code validation is case-insensitive."""
    response = await client.post(
        "/api/v1/discounts/validate",
        json={
            "code": "test10",  # Lowercase
            "subtotal": "50.00",
        },
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


@pytest.mark.asyncio
async def test_validate_discount_code_max_uses_reached(
    client: AsyncClient, db_session: AsyncSession, test_tenant
):
    """Test that discount is invalid when max uses reached."""
    discount = DiscountCode(
        tenant_id=test_tenant.id,
        code="MAXED",
        name="Maxed Out",
        discount_type=DiscountType.PERCENTAGE.value,
        amount=Decimal("10.00"),
        max_uses=1,
        current_uses=1,  # Already used
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        is_active=True,
    )
    db_session.add(discount)
    await db_session.commit()

    response = await client.post(
        "/api/v1/discounts/validate",
        json={
            "code": "MAXED",
            "subtotal": "50.00",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["valid"] is False
    assert "usage limit" in data["message"]


@pytest.mark.asyncio
async def test_validate_discount_code_per_customer_limit(
    client: AsyncClient, db_session: AsyncSession, test_tenant
):
    """Test per-customer usage limit."""
    discount = DiscountCode(
        tenant_id=test_tenant.id,
        code="ONCE",
        name="Once Per Customer",
        discount_type=DiscountType.PERCENTAGE.value,
        amount=Decimal("10.00"),
        max_uses_per_customer=1,
        valid_from=datetime.now(timezone.utc) - timedelta(days=1),
        is_active=True,
    )
    db_session.add(discount)
    await db_session.commit()
    await db_session.refresh(discount)

    # Create a mock order for usage tracking
    order = Order(
        tenant_id=test_tenant.id,
        order_number="TEST-001",
        customer_email="used@example.com",
        customer_name="Test User",
        shipping_address_line1="123 Test St",
        shipping_city="Test City",
        shipping_postcode="TE5T 1NG",
        shipping_method="Standard",
        subtotal=Decimal("50.00"),
        total=Decimal("50.00"),
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    # Record usage
    usage = DiscountUsage(
        tenant_id=test_tenant.id,
        discount_code_id=discount.id,
        order_id=order.id,
        customer_email="used@example.com",
        discount_amount=Decimal("5.00"),
    )
    db_session.add(usage)
    await db_session.commit()

    # Same customer should be rejected
    response = await client.post(
        "/api/v1/discounts/validate",
        json={
            "code": "ONCE",
            "subtotal": "50.00",
            "customer_email": "used@example.com",
        },
    )
    data = response.json()
    assert data["valid"] is False
    assert "maximum number of times" in data["message"]

    # Different customer should work
    response = await client.post(
        "/api/v1/discounts/validate",
        json={
            "code": "ONCE",
            "subtotal": "50.00",
            "customer_email": "new@example.com",
        },
    )
    data = response.json()
    assert data["valid"] is True


# ============================================
# Authentication Tests
# ============================================


@pytest.mark.asyncio
async def test_discount_endpoints_require_auth(unauthenticated_client: AsyncClient):
    """Test that admin endpoints require authentication."""
    # List
    response = await unauthenticated_client.get("/api/v1/discounts")
    assert response.status_code == 401

    # Create
    response = await unauthenticated_client.post(
        "/api/v1/discounts",
        json={
            "code": "TEST",
            "name": "Test",
            "discount_type": "percentage",
            "amount": "10",
            "valid_from": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert response.status_code == 401

    # Update
    response = await unauthenticated_client.patch(
        f"/api/v1/discounts/{uuid4()}",
        json={"name": "Updated"},
    )
    assert response.status_code == 401

    # Delete
    response = await unauthenticated_client.delete(f"/api/v1/discounts/{uuid4()}")
    assert response.status_code == 401

    # Validate also requires auth (uses tenant context)
    response = await unauthenticated_client.post(
        "/api/v1/discounts/validate",
        json={"code": "TEST", "subtotal": "50.00"},
    )
    assert response.status_code == 401
