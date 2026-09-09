"""Real PostgreSQL dispatch transactions, nested under an outer rollback."""

import asyncio
import copy
import hashlib
import json
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.commerce_bridge as bridge


async def main():
    checks = []

    def check(name, passed):
        checks.append({"check": name, "pass": bool(passed)})
        if not passed:
            raise AssertionError(name)

    tables = [
        "products",
        "product_variants",
        "orders",
        "order_items",
        "print_jobs",
        "commerce_orders",
        "commerce_receipts",
        "commerce_fulfilment_events",
    ]

    async def fingerprint(db):
        await db.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant, true)"),
            {"tenant": str(bridge.TENANT)},
        )
        return [
            await db.scalar(
                text(f"SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM {table} t")
            )
            for table in tables
        ]

    original = bridge.async_session_maker
    async with bridge.engine.connect() as connection:
        before = await fingerprint(connection)
        await connection.rollback()
        outer = await connection.begin()
        bridge.async_session_maker = async_sessionmaker(
            connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
            sync_session_class=bridge.CommerceSession,
        )
        try:
            async with bridge.async_session_maker() as db:
                mapping = await db.scalar(
                    select(bridge.CommerceOrder).where(bridge.CommerceOrder.woo_order_id == 603)
                )
                order_id = UUID(mapping.batchivo_order_id)
                order = await db.get(bridge.Order, order_id)
                check(
                    "Recorded refunded shipment fixture",
                    order.status == "shipped"
                    and order.payment_status == "REFUNDED"
                    and bool(order.shipped_at),
                )
                snapshot, effects = copy.deepcopy(mapping.snapshot), copy.deepcopy(mapping.effects)
                shipped, tracking = order.shipped_at, order.tracking_number
            command = bridge.DispatchCommand(event_id=uuid4(), order_id=603, state="delivered")

            async def apply(cmd):
                raw = json.dumps(cmd.model_dump(mode="json"), sort_keys=True).encode()
                return await bridge.record_dispatch(cmd, hashlib.sha256(raw).hexdigest())

            async def deny(name, cmd):
                try:
                    await apply(cmd)
                except HTTPException as error:
                    check(name, error.status_code in [409, 422])
                else:
                    check(name, False)

            await deny(
                "New dispatch remains forbidden after refund",
                command.model_copy(update={"event_id": uuid4(), "state": "shipped"}),
            )
            await deny(
                "Delivery cannot replace tracking",
                command.model_copy(update={"tracking_number": "REPLACEMENT"}),
            )
            await deny(
                "Unshipped refund cannot acquire delivery",
                command.model_copy(update={"order_id": 601}),
            )
            result = await apply(command)
            check("Late delivery recorded", result["status"] == "recorded")
            replay = await apply(command)
            check(
                "Exact retry returns same durable version",
                replay["status"] == "duplicate" and replay["version"] == result["version"],
            )
            await deny(
                "Reused command cannot change details",
                command.model_copy(update={"tracking_number": "CHANGED"}),
            )
            await deny(
                "Different event cannot deliver twice",
                command.model_copy(update={"event_id": uuid4()}),
            )
            async with bridge.async_session_maker() as db:
                mapping = await db.scalar(
                    select(bridge.CommerceOrder).where(bridge.CommerceOrder.woo_order_id == 603)
                )
                order = await db.get(bridge.Order, order_id)
                check(
                    "Financial and returns records preserved",
                    mapping.snapshot == snapshot
                    and mapping.effects == effects
                    and mapping.state == "refunded"
                    and order.payment_status == "REFUNDED",
                )
                check(
                    "Physical state and timestamps retained",
                    order.status == "delivered"
                    and bool(order.delivered_at)
                    and order.shipped_at == shipped
                    and order.tracking_number == tracking,
                )
                check(
                    "Restricted role remains in use",
                    await db.scalar(text("SELECT current_user")) == "mf_commerce_test",
                )
            after = await fingerprint(connection)
            check(
                "Products variants items jobs and commerce financial records unchanged",
                all(before[i] == after[i] for i in [0, 1, 3, 4, 5, 6]),
            )
        finally:
            bridge.async_session_maker = original
            await outer.rollback()
        check("Outer rollback restores all eight tables", before == await fingerprint(connection))
    print(
        json.dumps(
            {
                "checks": checks,
                "failed": sum(not c["pass"] for c in checks),
                "scope": "Actual restricted PostgreSQL transactions/savepoints with outer rollback. No payment calls or customer messages. Deployed browser/operator acceptance is separate.",
            }
        )
    )


asyncio.run(main())
