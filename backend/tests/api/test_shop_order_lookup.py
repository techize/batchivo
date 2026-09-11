"""Real ORM/HTTP storefront order boundaries, using disposable test data."""

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_shop_sales_channel
from app.database import get_db
from app.main import app
from app.models.order import Order
from app.models.sales_channel import SalesChannel
from app.models.tenant import Tenant


@pytest.mark.anyio
@pytest.mark.parametrize(
    "case",
    ["own", "email_case", "wrong_email", "other_tenant", "other_channel", "no_channel", "missing"],
)
async def test_order_lookup_boundary(db_session, test_tenant, case):
    other = Tenant(id=uuid4(), name="Other shop", slug="other-" + uuid4().hex)
    channel = SalesChannel(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Shop",
        platform_type="online_shop",
        is_active=True,
    )
    foreign = SalesChannel(
        id=uuid4(), tenant_id=other.id, name="Other", platform_type="online_shop", is_active=True
    )
    second = SalesChannel(
        id=uuid4(), tenant_id=test_tenant.id, name="Fair", platform_type="fair", is_active=True
    )
    db_session.add(other)
    await db_session.flush()
    db_session.add_all([channel, foreign, second])
    await db_session.flush()
    order = Order(
        tenant_id=other.id if case == "other_tenant" else test_tenant.id,
        sales_channel_id=foreign.id
        if case == "other_tenant"
        else second.id
        if case == "other_channel"
        else None
        if case == "no_channel"
        else channel.id,
        order_number="LOOKUP-" + uuid4().hex,
        status="shipped",
        customer_name="Synthetic customer",
        customer_email="fixture@example.invalid",
        shipping_address_line1="Test",
        shipping_city="Test",
        shipping_postcode="TEST",
        shipping_method="Standard",
        shipping_cost=Decimal("4.99"),
        subtotal=Decimal("9.99"),
        total=Decimal("14.98"),
    )
    db_session.add(order)
    await db_session.commit()

    async def context():
        return test_tenant, channel

    async def session():
        yield db_session

    app.dependency_overrides[get_shop_sales_channel] = context
    app.dependency_overrides[get_db] = session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            result = await client.get(
                "/api/v1/shop/orders/" + ("missing" if case == "missing" else order.order_number),
                params={
                    "email": "wrong@example.invalid"
                    if case == "wrong_email"
                    else " FIXTURE@EXAMPLE.INVALID "
                    if case == "email_case"
                    else order.customer_email
                },
            )
        if case in ["own", "email_case"]:
            assert result.status_code == 200, result.text
            assert result.json()["data"]["status"] == "shipped"
            assert result.headers["cache-control"] == "private, no-store"
            assert "shipping_address_line1" not in result.json()["data"]
        else:
            assert result.status_code == 404, result.text
            assert "Synthetic customer" not in result.text
    finally:
        app.dependency_overrides.clear()
