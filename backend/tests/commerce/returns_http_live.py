"""Read-only deployed HTTP/security and final physical-return reconciliation."""

import asyncio
import hashlib
import hmac
import json
import time
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select, text

from app.commerce_bridge import SECRET, CommerceOrder, Order, Product, async_session_maker


async def main():
    checks = []

    def check(name, value):
        checks.append({"check": name, "pass": bool(value)})
        if not value:
            raise AssertionError(name)

    async with async_session_maker() as db:

        async def fingerprint():
            return [
                await db.scalar(
                    text(
                        f"SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM {table} t"
                    )
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

        before = await fingerprint()
        mapping = await db.scalar(select(CommerceOrder).where(CommerceOrder.woo_order_id == 603))
        order = await db.get(Order, UUID(mapping.batchivo_order_id))
        product = await db.get(Product, UUID("65cf3926-cda4-438f-8dd5-c0851072b727"))
        check(
            "Native sold order remains shipped and fully refunded",
            order.status == "shipped"
            and order.payment_status == "REFUNDED"
            and mapping.snapshot["total_pence"] == 1898
            and mapping.effects["refunded_pence"] == 1898,
        )
        check(
            "One sold unit remains immutable",
            len(mapping.snapshot["lines"]) == 1 and mapping.snapshot["lines"][0]["quantity"] == 1,
        )
        ledger = mapping.effects["returns"]
        counts = ledger["lines"][str(mapping.snapshot["lines"][0]["line_id"])]
        check(
            "Received and inspected counts reconcile",
            counts == {"received": 1, "restocked": 1, "written_off": 0},
        )
        check(
            "One receive and one restock receipt only",
            len(ledger["receipts"]) == 2
            and sorted(r["action"] for r in ledger["receipts"].values()) == ["receive", "restock"],
        )
        check(
            "Original finite allocation preserved without automatic release",
            mapping.effects["stock"][0]["quantity"] == 1 and not mapping.effects["restored"],
        )
        check("Original isolated stock level restored exactly once", product.units_in_stock == 1)
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30) as client:

            async def post(path, payload, signed=True):
                raw = json.dumps(payload, separators=(",", ":")).encode()
                stamp = str(int(time.time()))
                headers = {"Content-Type": "application/json"}
                if signed:
                    headers.update(
                        {
                            "X-MF-Timestamp": stamp,
                            "X-MF-Signature": hmac.new(
                                SECRET, stamp.encode() + b"." + raw, hashlib.sha256
                            ).hexdigest(),
                        }
                    )
                return await client.post(
                    "/fulfilment/returns/" + path, content=raw, headers=headers
                )

            r = await post("review", {"order_id": 603}, False)
            check("Unsigned returns review refused", r.status_code in (401, 403))
            r = await post("apply", {"order_id": 603}, False)
            check("Unsigned return write refused", r.status_code in (401, 403))
            r = await post("review", {"order_id": 603})
            review = r.json()
            check(
                "Actual signed review verifies Square and saved quantities",
                r.status_code == 200 and review["ok"] and review["lines"][0]["restocked"] == 1,
            )
            stamp = r.headers.get("x-mf-timestamp", "")
            check(
                "HTTP response signature verifies",
                hmac.compare_digest(
                    r.headers.get("x-mf-signature", ""),
                    hmac.new(SECRET, stamp.encode() + b"." + r.content, hashlib.sha256).hexdigest(),
                ),
            )
            before_refund = await post("review", {"order_id": 557})
            check(
                "Signed review supports goods arriving before a refund",
                before_refund.status_code == 200
                and before_refund.json()["ok"]
                and before_refund.json()["refunded_pence"] == 0,
            )
            command = {
                "order_id": 603,
                "event_id": str(uuid4()),
                "revision": review["revision"],
                "line_id": review["lines"][0]["line_id"],
                "action": "restock",
                "quantity": 1,
                "actor_id": 1,
                "note": "Rejected HTTP acceptance probe",
            }
            r = await post("apply", command)
            check(
                "Already inspected goods cannot restock again",
                r.status_code == 200 and not r.json()["ok"] and r.json()["code"] == 409,
            )
            r = await post("apply", {**command, "quantity": True})
            check(
                "Boolean cannot masquerade as quantity",
                r.status_code == 200 and not r.json()["ok"] and r.json()["code"] == 422,
            )
            r = await post("apply", {**command, "quantity": 0})
            check("Zero quantity refused", not r.json()["ok"] and r.json()["code"] == 422)
            r = await post("apply", {**command, "revision": "0" * 64})
            check("Stale return revision held", not r.json()["ok"] and r.json()["code"] == 409)
            r = await post("review", {"order_id": 601})
            check(
                "Unshipped refunded order cannot enter returns flow",
                not r.json()["ok"] and r.json()["code"] == 409,
            )
        check(
            "All rejected and read-only probes leave eight tables unchanged",
            before == await fingerprint(),
        )
    print(
        json.dumps(
            {
                "checks": checks,
                "failed": sum(not c["pass"] for c in checks),
                "scope": "Actual signed HTTP, Square sandbox verification and restricted PostgreSQL. No new payment or refund submitted.",
            }
        )
    )


asyncio.run(main())
