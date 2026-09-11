"""Fence WooCommerce-owned effects and route native dispatch through its durable writer.

The registry is authoritative; order-number prefixes only detect missing mappings.
Legacy orders keep their existing behavior. Production activation remains a separate
release with explicit database, provider and version identity checks.
"""

import hashlib
import json
import os

from app.commerce_runtime import CommerceRuntime
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from sqlalchemy import text


async def commerce_order_id(db, order):
    # SQLite is used by legacy tests; the commerce integration requires PostgreSQL.
    dialect = db.bind.dialect.name
    if dialect != "postgresql":
        if (order.order_number or "").startswith("WOO-"):
            raise HTTPException(409, "WooCommerce order mapping unavailable")
        return None
    exists = await db.scalar(text("SELECT to_regclass('public.commerce_orders')"))
    if exists:
        value = await db.scalar(
            text("SELECT woo_order_id FROM commerce_orders WHERE batchivo_order_id=:id"),
            {"id": str(order.id)},
        )
        if value is not None:
            return int(value)
    if (order.order_number or "").startswith("WOO-"):
        raise HTTPException(409, "WooCommerce order mapping requires reconciliation")
    return None


async def reject_native_commerce_mutation(db, order):
    if await commerce_order_id(db, order) is not None:
        raise HTTPException(
            409,
            "This WooCommerce order uses the commerce workflow. Manage refunds, "
            "cancellations and customer emails in WooCommerce; use Ship/Deliver here "
            "for dispatch. Stock must not be deducted or restored again.",
        )


async def dispatch_native_commerce(db, order, tenant, state, tracking_number="", tracking_url=""):
    woo_id = await commerce_order_id(db, order)
    if woo_id is None:
        return None
    if order.tenant_id != tenant.id:
        raise HTTPException(404, "Order not found")
    try:
        CommerceRuntime.from_environment(os.environ)
    except RuntimeError:
        raise HTTPException(
            409, "WooCommerce dispatch adapter requires an activated release"
        ) from None
    from app.commerce_bridge import DispatchCommand, TENANT, record_dispatch

    if tenant.id != TENANT:
        raise HTTPException(404, "Order not found")
    try:
        command = DispatchCommand(
            event_id=uuid5(
                NAMESPACE_URL, f"mystmere:{tenant.id}:woocommerce:{woo_id}:fulfilment:{state}:v1"
            ),
            order_id=woo_id,
            state=state,
            tracking_number=tracking_number or "",
            tracking_url=tracking_url or "",
        )
    except ValueError:
        raise HTTPException(422, "Invalid commerce dispatch details")
    raw = json.dumps(
        command.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode()
    result = await record_dispatch(command, hashlib.sha256(raw).hexdigest())
    return {"message": f"Order {order.order_number}: {state} recorded", "commerce": result}
