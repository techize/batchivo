"""Actual native route dependencies and signed callback against disposable PostgreSQL."""

import base64
import hashlib
import hmac
import json
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.v1 import customer_account, customer_auth, payments, shop
from app.auth.customer_dependencies import create_customer_refresh_token, get_current_customer
from app.auth.dependencies import get_shop_sales_channel, get_shop_tenant
from app.database import get_db
from app.models.webhook_event import WebhookEvent
from app.services import commerce_handover as handover


async def probe_http(engine, check):
    app = FastAPI()
    for prefix, module in [
        ("/payments", payments),
        ("/shop", shop),
        ("/auth", customer_auth),
        ("/account", customer_account),
    ]:
        app.include_router(module.router, prefix=prefix)
    tenant = SimpleNamespace(id=handover.TENANT)
    customer = SimpleNamespace(id=uuid4(), tenant_id=handover.TENANT)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def database():
        async with sessions() as session:
            yield session

    # Authentication/context fixtures only. Ownership, locks, callback processing,
    # signature verification, persistence and route dependency wiring are real.
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_shop_tenant] = lambda: tenant
    app.dependency_overrides[get_shop_sales_channel] = lambda: (tenant, None)
    app.dependency_overrides[get_current_customer] = lambda: customer
    product = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text("CREATE TABLE products (id uuid PRIMARY KEY, tenant_id uuid NOT NULL)")
        )
        await conn.execute(
            text("INSERT INTO products VALUES (:id,:tenant)"),
            {"id": product, "tenant": handover.TENANT},
        )
        await conn.execute(text("CREATE TABLE orders (id uuid PRIMARY KEY)"))
        await conn.run_sync(WebhookEvent.__table__.create)
    refresh = create_customer_refresh_token(
        customer.id, handover.TENANT, "handover@example.invalid"
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://handover.test"
    ) as client:
        routes = [
            ("POST", "/payments/hosted-checkout", {}),
            ("POST", "/payments/process", {}),
            ("POST", "/shop/checkout/create-payment", {}),
            ("POST", "/shop/checkout/complete", {}),
            ("POST", "/auth/register", {}),
            ("POST", "/auth/login", {}),
            ("POST", "/auth/forgot-password", {}),
            ("POST", "/auth/reset-password", {}),
            ("POST", "/auth/verify-email", {}),
            ("POST", "/auth/resend-verification", {}),
            ("POST", "/auth/change-password", {}),
            ("POST", "/auth/refresh", {"refresh_token": refresh}),
            ("PUT", "/account/profile", {}),
            ("POST", f"/shop/products/{product}/reviews", {}),
            ("POST", f"/shop/products/{product}/reviews/{uuid4()}/helpful", {}),
        ]
        for method, path, body in routes:
            response = await client.request(method, path, json=body)
            check(
                "Native HTTP writer fenced: " + path.replace(str(product), "product"),
                response.status_code == 409,
            )
        response = await client.get("/payments/config")
        check(
            "Read-only payment configuration remains available during ownership fence",
            response.status_code == 200,
        )
        previous = payments.settings.square_webhook_signature_key
        key = "isolated-handover-signature-key"
        payments.settings.square_webhook_signature_key = key
        try:
            body = json.dumps(
                {"type": "handover.acceptance", "event_id": str(uuid4()), "data": {}}
            ).encode()
            signature = base64.b64encode(
                hmac.new(
                    key.encode(),
                    b"http://handover.test/payments/webhooks/square" + body,
                    hashlib.sha256,
                ).digest()
            ).decode()
            headers = {"x-square-hmacsha256-signature": signature}
            first = await client.post("/payments/webhooks/square", content=body, headers=headers)
            check(
                "Signed legacy callback persists successfully while legacy writers are fenced",
                first.status_code == 200 and first.json()["status"] == "processed",
            )
            duplicate = await client.post(
                "/payments/webhooks/square", content=body, headers=headers
            )
            check(
                "Actual PostgreSQL callback receipt prevents duplicate processing",
                duplicate.status_code == 200 and duplicate.json()["status"] == "duplicate",
            )
            async with engine.begin() as conn:
                await conn.execute(
                    text("ALTER TABLE webhook_events RENAME TO webhook_events_unavailable")
                )
            failed = await client.post("/payments/webhooks/square", content=body, headers=headers)
            check(
                "Actual unavailable receipt table returns retryable HTTP 503",
                failed.status_code == 503,
            )
            async with engine.begin() as conn:
                await conn.execute(
                    text("ALTER TABLE webhook_events_unavailable RENAME TO webhook_events")
                )
            recovered = await client.post(
                "/payments/webhooks/square", content=body, headers=headers
            )
            check(
                "Legacy callback recovers without a duplicate after database availability returns",
                recovered.status_code == 200 and recovered.json()["status"] == "duplicate",
            )
        finally:
            payments.settings.square_webhook_signature_key = previous
