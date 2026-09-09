"""Validate and attach stable job UUIDs to existing isolated commerce effects.
No stock/order/job status changes. One transaction; dry run rolls back.
"""

import asyncio
import json
import sys
from uuid import UUID

from sqlalchemy import select
from app.commerce_bridge import (
    CommerceOrder,
    PrintJob,
    RUNTIME,
    TENANT,
    async_session_maker,
    reservation_order_lock,
)


async def main():
    if not RUNTIME.isolated:
        raise RuntimeError("Only isolated test mappings may be backfilled by this entry point")
    counts = {"orders": 0, "jobs": 0, "changed": 0, "applied": "--apply" in sys.argv}
    async with async_session_maker() as db:
        async with db.begin():
            ids = (
                await db.scalars(
                    select(CommerceOrder.woo_order_id).order_by(CommerceOrder.woo_order_id)
                )
            ).all()
            for order_id in ids:
                await reservation_order_lock(db, order_id)
                mapping = await db.scalar(
                    select(CommerceOrder)
                    .where(CommerceOrder.woo_order_id == order_id)
                    .with_for_update()
                )
                finite = {
                    (s["product_id"], s["variant_id"]) for s in mapping.effects.get("stock", [])
                }
                identities = []
                for line in mapping.snapshot["lines"]:
                    if (line["product_id"], line.get("variant_id")) in finite:
                        continue
                    jobs = (
                        await db.scalars(
                            select(PrintJob)
                            .where(
                                PrintJob.tenant_id == TENANT,
                                PrintJob.reference
                                == RUNTIME.job_reference(order_id, line["line_id"]),
                            )
                            .with_for_update()
                        )
                    ).all()
                    if len(jobs) != 1:
                        raise RuntimeError(
                            "Expected exactly one commerce job for order " + str(order_id)
                        )
                    job = jobs[0]
                    if (
                        job.product_id != UUID(line["product_id"])
                        or job.quantity != line["quantity"]
                    ):
                        raise RuntimeError(
                            "Job product/quantity mismatch for order " + str(order_id)
                        )
                    notes = json.loads(job.notes or "{}")
                    if (
                        notes.get("variant_id") != line.get("variant_id")
                        or notes.get("sku") != line["sku"]
                        or notes.get("option") != line["option"]
                    ):
                        raise RuntimeError(
                            "Job option identity mismatch for order " + str(order_id)
                        )
                    identities.append({"id": str(job.id), "line_id": line["line_id"]})
                identities.sort(key=lambda x: str(x["line_id"]))
                previous = sorted(mapping.effects.get("jobs", []), key=lambda x: str(x["line_id"]))
                if previous and previous != identities:
                    raise RuntimeError("Existing UUID mapping differs for order " + str(order_id))
                counts["orders"] += 1
                counts["jobs"] += len(identities)
                if "jobs" not in mapping.effects:
                    mapping.effects = {**mapping.effects, "jobs": identities}
                    counts["changed"] += 1
            if "--apply" not in sys.argv:
                await db.rollback()
    print(json.dumps(counts))


if __name__ == "__main__":
    asyncio.run(main())
