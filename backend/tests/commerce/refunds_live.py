"""Readback and rejected-event tests on real sandbox refunds for retained fixture431."""

import asyncio
import hashlib
import hmac
import json
import time
from uuid import uuid4
import httpx
from sqlalchemy import select, text
from app.commerce_bridge import (
    CommerceOrder,
    Order,
    PrintJob,
    TENANT,
    SECRET,
    async_session_maker,
    JobStatus,
)


async def main():
    checks = []

    def check(name, ok):
        checks.append({"check": name, "pass": bool(ok)})

    async with async_session_maker() as db:
        mapping = await db.scalar(select(CommerceOrder).where(CommerceOrder.woo_order_id == 431))
        order = await db.scalar(select(Order).where(Order.id == mapping.batchivo_order_id))
        before = await db.scalar(
            text("SELECT md5(row_to_json(t)::text) FROM commerce_orders t WHERE woo_order_id=431")
        )
        jobs = (
            await db.scalars(
                select(PrintJob).where(
                    PrintJob.reference.like("WOO-TEST-431:%"), PrintJob.tenant_id == TENANT
                )
            )
        ).all()
        target = mapping.effects.get("refunded_pence", 0)
        check("verified cumulative refund is partial or full", target in [100, 2997])
        check(
            "dispatch/delivery preserved",
            order.status == "delivered"
            and order.shipped_at is not None
            and order.delivered_at is not None,
        )
        check(
            "both completed manufacturing jobs preserved",
            len(jobs) == 2 and all(j.status == JobStatus.COMPLETED for j in jobs),
        )
        check("no automatic post-dispatch stock restoration", not mapping.effects.get("restored"))
        check(
            "payment status reflects verified refund",
            order.payment_status == ("REFUNDED" if target == 2997 else "PARTIALLY_REFUNDED"),
        )
        check(
            "provider refund ledger totals reconcile",
            sum(r["amount_pence"] for r in mapping.effects.get("refunds", [])) == target
            and all(r["status"] == "COMPLETED" for r in mapping.effects.get("refunds", [])),
        )
        if target == 2997:
            check("return/goods review recorded", bool(mapping.effects.get("refund_review")))
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30) as client:

        async def post(data):
            raw = json.dumps(data, separators=(",", ":")).encode()
            stamp = str(int(time.time()))
            sig = hmac.new(SECRET, stamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
            return await client.post(
                "/events",
                content=raw,
                headers={
                    "Content-Type": "application/json",
                    "X-MF-Timestamp": stamp,
                    "X-MF-Signature": sig,
                },
            )

        base = {**mapping.snapshot, "version": mapping.version + 1, "event_id": str(uuid4())}
        regression = {
            **base,
            "state": "refunded" if target == 2997 else "completed",
            "refunded_pence": 0,
            "refund_ids": [],
        }
        response = await post(regression)
        check("refund amount regression rejected", response.status_code in [409, 422])
        altered = {**base, "refunded_pence": target + 1}
        response = await post(altered)
        check("unverified extra penny rejected", response.status_code in [409, 422])
        duplicate = {**base, "refund_ids": mapping.snapshot.get("refund_ids", []) * 2}
        response = await post(duplicate)
        check("duplicate refund identities rejected", response.status_code == 422)
    async with async_session_maker() as db:
        after = await db.scalar(
            text("SELECT md5(row_to_json(t)::text) FROM commerce_orders t WHERE woo_order_id=431")
        )
        check("rejected events leave mapping unchanged", before == after)
    print(
        json.dumps(
            {
                "order_id": 431,
                "verified_refunded_pence": target,
                "checks": checks,
                "failed": sum(not c["pass"] for c in checks),
            }
        )
    )


asyncio.run(main())
