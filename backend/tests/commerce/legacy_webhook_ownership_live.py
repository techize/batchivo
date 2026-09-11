"""Real isolated PostgreSQL callback processing, including commits, in an outer rollback.

Events are constructed signed fixtures; no event is claimed as delivered by Square.
Actual provider/payment evidence is retained separately in runtime/browser reports.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.commerce_bridge import RUNTIME, engine, TENANT, CommerceOrder
from app.models.order import Order
from app.models.webhook_event import WebhookEvent, WebhookDeadLetter
from app.models.payment_log import PaymentLog
from app.services.square_webhook_service import SquareWebhookService

logging.getLogger("app.services.square_webhook_service").setLevel(logging.CRITICAL)


async def main():
    if not RUNTIME.isolated:
        raise RuntimeError("Offline ownership fixtures require isolated database")
    checks = []

    def check(name, value):
        checks.append({"check": name, "pass": bool(value)})
        if not value:
            raise RuntimeError(name)

    tables = [
        "orders",
        "order_items",
        "products",
        "product_variants",
        "print_jobs",
        "commerce_orders",
        "commerce_receipts",
        WebhookEvent.__tablename__,
        WebhookDeadLetter.__tablename__,
        PaymentLog.__tablename__,
    ]

    async def fingerprints(conn):
        return {
            table: await conn.scalar(
                text(f"SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM {table} t")
            )
            for table in tables
        }

    async with engine.connect() as connection:
        before = await fingerprints(connection)
        await connection.rollback()
        outer = await connection.begin()
        try:
            async with AsyncSession(
                bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
            ) as db:
                service = SquareWebhookService(db)
                key = uuid4().hex
                url = "https://callback-rehearsal.invalid/square"
                body = b'{"type":"payment.updated"}'
                signature = base64.b64encode(
                    hmac.new(key.encode(), url.encode() + body, hashlib.sha256).digest()
                ).decode()
                check(
                    "actual signature verifier accepts correct URL and bytes",
                    await service.verify_signature(body, signature, key, url),
                )
                check(
                    "missing signature configuration fails closed",
                    not await service.verify_signature(body, signature, "", url),
                )
                check(
                    "changed notification URL rejected",
                    not await service.verify_signature(body, signature, key, url + "/changed"),
                )
                count = await db.scalar(text("SELECT count(*) FROM webhook_events"))
                rejected = await service.process_webhook(
                    {"event_id": str(uuid4()), "type": "payment.updated"}, signature_valid=False
                )
                check(
                    "failed authentication has no event or business writes",
                    rejected["status"] == "rejected"
                    and await db.scalar(text("SELECT count(*) FROM webhook_events")) == count,
                )
                for oid in [468, 571, 574]:
                    mapping = await db.scalar(
                        select(CommerceOrder).where(CommerceOrder.woo_order_id == oid)
                    )
                    payment_id = mapping.snapshot["payment_id"]
                    native_id = mapping.batchivo_order_id
                    original = await db.scalar(
                        text(
                            "SELECT md5(row_to_json(o)::text) FROM orders o WHERE id=CAST(:id AS uuid)"
                        ),
                        {"id": native_id},
                    )
                    for event_type in [
                        "payment.created",
                        "payment.updated",
                        "payment.failed",
                        "refund.created",
                        "refund.updated",
                    ]:
                        payment = {
                            "id": payment_id,
                            "status": "COMPLETED",
                            "amount_money": {
                                "amount": mapping.snapshot["total_pence"],
                                "currency": "GBP",
                            },
                        }
                        refund = {
                            "id": "fixture-" + uuid4().hex,
                            "payment_id": payment_id,
                            "status": "COMPLETED",
                            "amount_money": {"amount": 1, "currency": "GBP"},
                        }
                        event = {
                            "event_id": str(uuid4()),
                            "type": event_type,
                            "data": {
                                "object": {"payment": payment}
                                if event_type.startswith("payment.")
                                else {"refund": refund}
                            },
                        }
                        raw = json.dumps(event).encode()
                        signed = base64.b64encode(
                            hmac.new(key.encode(), url.encode() + raw, hashlib.sha256).digest()
                        ).decode()
                        verified = await service.verify_signature(raw, signed, key, url)
                        result = await service.process_webhook(event, signature_valid=verified)
                        check(
                            f"{oid} {event_type} acknowledged with Woo ownership",
                            result["status"] == "processed"
                            and result["result"].get("order_owner") == "woocommerce"
                            and result["result"].get("woo_order_id") == oid,
                        )
                        duplicate = await service.process_webhook(event, signature_valid=verified)
                        check(
                            f"{oid} {event_type} exact duplicate acknowledged",
                            duplicate["status"] == "duplicate",
                        )
                    actual = await db.scalar(
                        text(
                            "SELECT md5(row_to_json(o)::text) FROM orders o WHERE id=CAST(:id AS uuid)"
                        ),
                        {"id": native_id},
                    )
                    check(
                        f"{oid} late payment and partial refund events preserve entire order",
                        actual == original,
                    )
                legacy = Order(
                    tenant_id=TENANT,
                    order_number="LEGACY-WEBHOOK-" + uuid4().hex,
                    customer_email="legacy-webhook@example.invalid",
                    customer_name="Isolated fixture",
                    shipping_address_line1="1 Fixture Lane",
                    shipping_city="Test",
                    shipping_postcode="SS1 1AA",
                    shipping_country="United Kingdom",
                    shipping_method="Fixture delivery",
                    subtotal=Decimal("10"),
                    total=Decimal("10"),
                    payment_id="fixture-" + uuid4().hex,
                    payment_provider="square",
                    payment_status="PENDING",
                )
                db.add(legacy)
                await db.commit()
                event = {
                    "event_id": str(uuid4()),
                    "type": "payment.updated",
                    "data": {
                        "object": {"payment": {"id": legacy.payment_id, "status": "COMPLETED"}}
                    },
                }
                result = await service.process_webhook(event)
                await db.refresh(legacy)
                check(
                    "ordinary legacy callback still updates its legacy order",
                    result["status"] == "processed"
                    and legacy.payment_status == "COMPLETED"
                    and "order_owner" not in result["result"],
                )
        finally:
            await outer.rollback()
        after = await fingerprints(connection)
        for table in tables:
            check(table + " unchanged after transactional rehearsal", before[table] == after[table])
    report = {
        "checks": checks,
        "failed": sum(not c["pass"] for c in checks),
        "scope": "Constructed HMAC-signed late/duplicate/partial-refund events through actual deployed legacy Square service and real PostgreSQL savepoint commits, all rolled back. Actual legacy normal behavior exercised. No external provider request or production mutation.",
    }
    print(json.dumps(report))


asyncio.run(main())
