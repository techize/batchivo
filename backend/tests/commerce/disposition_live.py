"""Real sandbox refund and restricted PostgreSQL decision checks, rolled back."""

import asyncio
import copy
import json
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text

from app import commerce_bridge as bridge
from app import commerce_disposition as module
from app.commerce_returns import lines_for_review


async def main():
    checks = []

    def check(name, passed):
        checks.append({"check": name, "pass": bool(passed)})
        if not passed:
            raise AssertionError(name)

    async def fingerprint(db):
        return [
            await db.scalar(
                text(f"SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM {table} t")
            )
            for table in [
                "products",
                "product_variants",
                "orders",
                "order_items",
                "print_jobs",
                "commerce_orders",
                "commerce_receipts",
                "commerce_fulfilment_events",
            ]
        ]

    async with bridge.async_session_maker() as db:
        before = await fingerprint(db)
        try:
            mapping, order, jobs, rows = await module.review_in_transaction(db, 605)
            check(
                "Actual mixed browser order and completed Square partial refund",
                mapping.snapshot["total_pence"] == 3397
                and mapping.effects["refunded_pence"] == 999
                and len(rows) == 2
                and len(jobs) == 1,
            )
            snapshot = copy.deepcopy(mapping.snapshot)
            base = copy.deepcopy(mapping.effects)
            job = next(iter(jobs.values()))
            pto = next(r for r in rows if r["manufacturing_status"])
            finite = next(r for r in rows if not r["manufacturing_status"])
            product = await db.get(
                bridge.Product,
                __import__("uuid").UUID(
                    next(l for l in snapshot["lines"] if l["line_id"] == finite["line_id"])[
                        "product_id"
                    ]
                ),
            )
            stock = product.units_in_stock

            def command(cancelled=None):
                return module.Command(
                    order_id=605,
                    event_id=uuid4(),
                    revision=module.revision(mapping, order),
                    cancelled=cancelled or {str(r["line_id"]): 0 for r in rows},
                    actor_id=1,
                    note="Sandbox rollback fulfilment decision evidence",
                )

            async def deny(name, cmd):
                try:
                    await module.apply_in_transaction(db, cmd)
                except HTTPException as e:
                    check(name, e.status_code in (409, 422, 503))
                else:
                    check(name, False)

            await deny(
                "Every sold line must be explicitly reviewed", command({str(pto["line_id"]): 1})
            )
            await deny(
                "Cannot cancel more than sold",
                command({str(pto["line_id"]): 3, str(finite["line_id"]): 0}),
            )
            await deny(
                "Cannot cancel all goods through partial financial release",
                command({str(pto["line_id"]): 2, str(finite["line_id"]): 1}),
            )
            job.status = bridge.JobStatus.PRINTING
            await deny(
                "Started manufacturing cannot be reduced",
                command({str(pto["line_id"]): 1, str(finite["line_id"]): 0}),
            )
            job.status = bridge.JobStatus.PENDING
            old_reference = job.reference
            job.reference = "CHANGED"
            await deny("Changed manufacturing identity fails closed", command())
            job.reference = old_reference
            payment = await bridge.verify_payment(bridge.Event.model_validate(snapshot))
            check(
                "Unreviewed partial refund holds fulfilment",
                not module.refund_release_valid(mapping.effects, payment),
            )
            cmd = command({str(pto["line_id"]): 1, str(finite["line_id"]): 0})
            result = await module.apply_in_transaction(db, cmd)
            check(
                "Partial cancellation reduces pending manufacturing from two to one",
                result["status"] == "recorded"
                and job.quantity == 1
                and job.status == bridge.JobStatus.PENDING,
            )
            check(
                "Reviewed exact refund releases remaining goods",
                module.refund_release_valid(mapping.effects, payment),
            )
            check(
                "Original sold snapshot and finite stock preserved",
                mapping.snapshot == snapshot and product.units_in_stock == stock,
            )
            check(
                "Exact retry is a durable duplicate",
                (await module.apply_in_transaction(db, cmd))["status"] == "duplicate"
                and job.quantity == 1,
            )
            await deny(
                "Same command identity cannot change details",
                cmd.model_copy(update={"note": "Different details"}),
            )
            await deny(
                "Another tab must refresh stale revision",
                cmd.model_copy(update={"event_id": uuid4()}),
            )
            await deny("Cancelled quantities cannot be reversed", command())
            changed = copy.deepcopy(payment)
            changed["refund_ids"].append("synthetic-later-refund")
            check(
                "Later pending refund identity invalidates approval",
                not module.refund_release_valid(mapping.effects, changed),
            )
            changed = copy.deepcopy(payment)
            changed["refunded_money"]["amount"] += 1
            check(
                "Later changed money invalidates approval",
                not module.refund_release_valid(mapping.effects, changed),
            )
            # Independent finite-stock decision, within the same outer rollback.
            cmd2 = command({str(pto["line_id"]): 1, str(finite["line_id"]): 1})
            await module.apply_in_transaction(db, cmd2)
            check(
                "Cancelled finite allocation returns stock once",
                product.units_in_stock == stock + 1
                and sum(x["quantity"] for x in mapping.effects["stock"]) == 0,
            )
            await module.apply_in_transaction(db, cmd2)
            check(
                "Finite cancellation replay cannot return stock twice",
                product.units_in_stock == stock + 1,
            )
            review = lines_for_review(mapping)
            check(
                "Physical returns exclude cancelled quantities",
                all(
                    r["shipped_quantity"] == (0 if r["line_id"] == finite["line_id"] else 1)
                    for r in review
                ),
            )
            check(
                "Original stock allocation retained for audit",
                mapping.effects["disposition"]["original_stock"] == base["stock"],
            )
            check(
                "All decisions retain operator and evidence",
                len(mapping.effects["disposition"]["receipts"]) == 2
                and all(
                    r["actor_id"] == 1 for r in mapping.effects["disposition"]["receipts"].values()
                ),
            )
        finally:
            await db.rollback()
        check(
            "Rollback preserves all eight persisted business tables",
            before == await fingerprint(db),
        )
    print(
        json.dumps(
            {
                "checks": checks,
                "failed": sum(not x["pass"] for x in checks),
                "scope": "Actual completed Square sandbox refund GETs and restricted PostgreSQL row locks/transactions. Mutated refund copies only test approval invalidation. All business mutations rolled back; browser decision follows separately.",
            }
        )
    )


asyncio.run(main())
