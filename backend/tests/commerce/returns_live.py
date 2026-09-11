"""Rollback checks against browser fixture603 and real Square payment/refund GETs.

The return ledger is reset only inside the rolled-back transaction. A temporary
allocation classification exercises the print-to-order guard. All persisted
stock, existing return receipts and financial history must remain unchanged.
"""

import asyncio
import copy
import importlib.util
import json
import logging
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from app.commerce_bridge import Product, async_session_maker

spec = importlib.util.spec_from_file_location("returns_under_test", "/tmp/mf-commerce-returns.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
logging.disable(logging.CRITICAL)


async def main():
    checks = []

    def check(name, passed):
        checks.append({"check": name, "pass": bool(passed)})
        if not passed:
            raise AssertionError(name)

    async def deny(name, command):
        try:
            await module.apply_return_in_transaction(db, command)
        except HTTPException as error:
            check(name, error.status_code in (409, 422, 503))
            return
        check(name, False)

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
                "commerce_fulfilment_events",
                "commerce_receipts",
            ]
        ]

    async with async_session_maker() as db:
        before = await fingerprint(db)
        try:
            mapping, order = await module.load_order(db, 603)
            check(
                "Fresh refunded finite-stock fixture was dispatched",
                bool(order.shipped_at) and order.payment_status == "REFUNDED",
            )
            await module.verify_refunds(mapping, order)
            check("Actual Square payment and completed refunds reconcile", True)
            original_snapshot = copy.deepcopy(mapping.snapshot)
            original_effects = copy.deepcopy(mapping.effects)
            original_effects.pop("returns", None)
            mapping.effects = copy.deepcopy(original_effects)
            line = mapping.snapshot["lines"][0]
            temporary = copy.deepcopy(mapping.effects)
            temporary["stock"] = []
            mapping.effects = temporary
            await db.flush()

            def command(action="receive", quantity=1, **kwargs):
                return module.ReturnCommand(
                    order_id=603,
                    event_id=uuid4(),
                    revision=module.revision(mapping, order),
                    line_id=line["line_id"],
                    action=action,
                    quantity=quantity,
                    actor_id=1,
                    note="Synthetic rollback inspection only",
                    **kwargs,
                )

            await deny("Cannot inspect goods before receiving them", command("write_off"))
            await deny("Cannot receive more than sold", command(quantity=line["quantity"] + 1))
            receive = command()
            result = await module.apply_return_in_transaction(db, receive)
            check(
                "Received goods remain awaiting inspection",
                result["status"] == "recorded"
                and module.lines_for_review(mapping)[0]["awaiting_inspection"] == 1,
            )
            check(
                "Exact replay returns duplicate",
                (await module.apply_return_in_transaction(db, receive))["status"] == "duplicate",
            )
            await deny(
                "Reused command cannot change quantity", receive.model_copy(update={"quantity": 2})
            )
            await deny(
                "Another tab cannot reuse old revision",
                receive.model_copy(update={"event_id": uuid4()}),
            )
            await deny("Print-to-order goods cannot inflate finite stock", command("restock"))
            await module.apply_return_in_transaction(db, command("write_off"))
            check(
                "Inspected write-off does not erase financial snapshot",
                module.lines_for_review(mapping)[0]["written_off"] == 1
                and mapping.snapshot == original_snapshot,
            )
            await deny("Inspected goods cannot be inspected twice", command("write_off"))
            check(
                "Audit records actor and evidence note",
                all(
                    r["actor_id"] == 1 and r["note"] == "Synthetic rollback inspection only"
                    for r in mapping.effects["returns"]["receipts"].values()
                ),
            )
            # A temporary allocation exercises the finite branch without inventing
            # a persisted shipment/payment or changing the retained fixture.
            mapping.effects = copy.deepcopy(original_effects)
            effects = copy.deepcopy(mapping.effects)
            effects["stock"] = [
                {
                    "product_id": line["product_id"],
                    "variant_id": line.get("variant_id"),
                    "quantity": line["quantity"],
                }
            ]
            mapping.effects = effects
            await db.flush()
            from app.commerce_bridge import ProductVariant

            cls = ProductVariant if line.get("variant_id") else Product
            stock = await db.get(cls, UUID(line.get("variant_id") or line["product_id"]))
            stock_before = stock.units_in_stock
            await module.apply_return_in_transaction(db, command())
            inspect = command("restock")
            await module.apply_return_in_transaction(db, inspect)
            check(
                "Finite stock increases by inspected quantity only",
                stock.units_in_stock == stock_before + 1,
            )
            check(
                "Restock replay never increments twice",
                (await module.apply_return_in_transaction(db, inspect))["status"] == "duplicate"
                and stock.units_in_stock == stock_before + 1,
            )
            await deny("Restock cannot exceed received quantity", command("restock"))
            check(
                "Sold quantities and captured money remain unchanged",
                mapping.snapshot == original_snapshot,
            )
            saved = order.shipped_at
            order.shipped_at = None
            await deny("Unshipped refunds cannot be treated as received returns", command())
            order.shipped_at = saved
            effects = copy.deepcopy(mapping.effects)
            effects["restored"] = True
            mapping.effects = effects
            await deny("Automatically released stock cannot be restored again", command())
            check(
                "Database writes use restricted commerce role",
                await db.scalar(text("SELECT current_user")) == "mf_commerce_test",
            )
        finally:
            await db.rollback()
        check("Rollback restores all eight protected tables", await fingerprint(db) == before)
    async with async_session_maker() as db:
        before = await fingerprint(db)
        try:
            mapping, order = await module.load_order(db, 557)
            await module.verify_refunds(mapping, order)
            check(
                "Shipped paid goods can be received before a refund",
                order.payment_status == "COMPLETED" and not mapping.effects.get("refunded_pence"),
            )
            original = copy.deepcopy(mapping.snapshot)
            effects = copy.deepcopy(mapping.effects)
            effects.pop("returns", None)
            mapping.effects = effects
            cmd = module.ReturnCommand(
                order_id=557,
                event_id=uuid4(),
                revision=module.revision(mapping, order),
                line_id=mapping.snapshot["lines"][0]["line_id"],
                action="receive",
                quantity=1,
                actor_id=1,
                note="Synthetic pre-refund receipt; rollback only",
            )
            await module.apply_return_in_transaction(db, cmd)
            check(
                "Pre-refund receipt leaves payment and sold snapshot unchanged",
                mapping.snapshot == original and order.payment_status == "COMPLETED",
            )
            check(
                "Pre-refund goods remain awaiting inspection",
                module.lines_for_review(mapping)[0]["awaiting_inspection"] == 1,
            )
        finally:
            await db.rollback()
        check("Pre-refund probe restores all eight tables", await fingerprint(db) == before)
    print(
        json.dumps(
            {
                "checks": checks,
                "failed": sum(not c["pass"] for c in checks),
                "scope": "Actual restricted-role PostgreSQL and Square sandbox reads, temporary print-to-order classification branch rolled back. No committed return, new transaction, customer email or physical manufacturing. Fresh finite browser payment is independently reconciled.",
            }
        )
    )


asyncio.run(main())
