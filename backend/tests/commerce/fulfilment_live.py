"""Live isolated fulfilment acceptance on retained sandbox fixture 431, never order 468.
Runs native queue service transitions against a simulated printer without network settings.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import sys
import time
from uuid import uuid5, NAMESPACE_URL
import httpx
from sqlalchemy import select, text
from app.commerce_bridge import (
    CommerceOrder,
    CommerceFulfilmentEvent,
    PrintJob,
    JobStatus,
    Tenant,
    TENANT,
    SECRET,
    async_session_maker,
)
from app.models.printer import Printer
from app.services.print_queue_service import PrintQueueService

logging.disable(logging.CRITICAL)
ORDER = 431
SHIP = str(uuid5(NAMESPACE_URL, "mystmere-test-431-dispatch-v1"))
DELIVER = str(uuid5(NAMESPACE_URL, "mystmere-test-431-delivery-v2"))


async def main():
    checks = []
    error = None

    def check(name, ok):
        checks.append({"check": name, "pass": bool(ok)})
        if not ok:
            raise AssertionError(name)

    async def protected(db):
        return [
            await db.scalar(text(q))
            for q in [
                "SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM products t",
                "SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM product_variants t",
                "SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM commerce_orders t WHERE woo_order_id=468",
                "SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM orders t WHERE id=(SELECT batchivo_order_id::uuid FROM commerce_orders WHERE woo_order_id=468)",
                "SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) FROM print_jobs t WHERE reference NOT LIKE 'WOO-TEST-431:%'",
            ]
        ]

    async with async_session_maker() as db:
        before = await protected(db)
    mode = sys.argv[1] if len(sys.argv) > 1 else "ship"
    command = {
        "event_id": SHIP,
        "order_id": ORDER,
        "state": "shipped",
        "tracking_number": "TEST-431-NOT-A-PARCEL",
        "tracking_url": "https://test.mystmereforge.co.uk/my-account/orders/",
    }
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=30) as client:

        async def post(path, data, bad=False):
            raw = json.dumps(data, separators=(",", ":")).encode()
            stamp = str(int(time.time()))
            sig = hmac.new(SECRET, stamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
            return await client.post(
                "/fulfilment/" + path,
                content=raw,
                headers={
                    "Content-Type": "application/json",
                    "X-MF-Timestamp": stamp,
                    "X-MF-Signature": "0" * 64 if bad else sig,
                },
            )

        try:
            check(
                "unsigned dispatch rejected",
                (await post("dispatch", command, True)).status_code == 401,
            )
            check(
                "non-HTTPS tracking rejected",
                (
                    await post("dispatch", {**command, "tracking_url": "javascript:alert(1)"})
                ).status_code
                == 422,
            )
            check(
                "embedded tracking credentials rejected",
                (
                    await post(
                        "dispatch", {**command, "tracking_url": "https://user:pass@example.com/"}
                    )
                ).status_code
                == 422,
            )
            check(
                "unknown order rejected",
                (
                    await post(
                        "dispatch",
                        {
                            **command,
                            "event_id": str(uuid5(NAMESPACE_URL, "unknown-order-test")),
                            "order_id": 99999999,
                        },
                    )
                ).status_code
                == 404,
            )
            async with async_session_maker() as db:
                mapping = await db.scalar(
                    select(CommerceOrder).where(CommerceOrder.woo_order_id == ORDER)
                )
                check(
                    "fixture is retained paid sandbox mapping",
                    mapping is not None
                    and mapping.snapshot["payment_id"]
                    and mapping.state == "processing",
                )
                jobs = (
                    await db.scalars(
                        select(PrintJob).where(
                            PrintJob.tenant_id == TENANT, PrintJob.reference.like("WOO-TEST-431:%")
                        )
                    )
                ).all()
                check(
                    "two distinct fixture jobs retained",
                    len(jobs) == 2
                    and {j.reference for j in jobs} == {"WOO-TEST-431:4", "WOO-TEST-431:5"}
                    and all(j.quantity == 1 for j in jobs),
                )
                already = await db.scalar(
                    select(CommerceFulfilmentEvent).where(CommerceFulfilmentEvent.event_id == SHIP)
                )
            if mode == "ship":
                if not already:
                    check(
                        "delivery before dispatch rejected",
                        (
                            await post(
                                "dispatch",
                                {"event_id": DELIVER, "order_id": ORDER, "state": "delivered"},
                            )
                        ).status_code
                        == 409,
                    )
                    if any(j.status != JobStatus.COMPLETED for j in jobs):
                        check(
                            "pending manufacturing blocks dispatch",
                            (await post("dispatch", command)).status_code == 409,
                        )
                    async with async_session_maker() as db:
                        tenant = await db.get(Tenant, TENANT)
                        service = PrintQueueService(db, tenant)
                        printer = await db.scalar(
                            select(Printer).where(
                                Printer.tenant_id == TENANT,
                                Printer.name == "Commerce simulated printer 431",
                            )
                        )
                        if not printer:
                            printer = Printer(
                                tenant_id=TENANT,
                                name="Commerce simulated printer 431",
                                current_status="idle",
                                is_active=True,
                            )
                            db.add(printer)
                            await db.commit()
                            await db.refresh(printer)
                        for job in jobs:
                            current = await service.get_job(job.id)
                            if current.status == JobStatus.PENDING:
                                check(
                                    job.reference + " native assign",
                                    (await service.assign_to_printer(job.id, printer.id)).status
                                    == JobStatus.QUEUED,
                                )
                            current = await service.get_job(job.id)
                            if current.status == JobStatus.QUEUED:
                                check(
                                    job.reference + " native start",
                                    (await service.start_printing(job.id)).status
                                    == JobStatus.PRINTING,
                                )
                            current = await service.get_job(job.id)
                            if current.status == JobStatus.PRINTING:
                                check(
                                    job.reference + " native complete",
                                    (await service.complete_job(job.id)).status
                                    == JobStatus.COMPLETED,
                                )
                        printer.is_active = False
                        await db.commit()
                response = await post("dispatch", command)
                check(
                    "real dispatch verifies Square sandbox and records once; HTTP "
                    + str(response.status_code),
                    response.status_code == 200 and response.json()["version"] == 1,
                )
                check(
                    "identical command retry returns duplicate",
                    (await post("dispatch", command)).json().get("status") == "duplicate",
                )
                check(
                    "reused command cannot change tracking",
                    (await post("dispatch", {**command, "tracking_number": "changed"})).status_code
                    == 409,
                )
            elif mode == "deliver":
                response = await post(
                    "dispatch", {"event_id": DELIVER, "order_id": ORDER, "state": "delivered"}
                )
                check(
                    "delivery recorded after dispatch",
                    response.status_code == 200 and response.json()["version"] == 2,
                )
                check(
                    "delivery command replay idempotent",
                    (
                        await post(
                            "dispatch",
                            {"event_id": DELIVER, "order_id": ORDER, "state": "delivered"},
                        )
                    )
                    .json()
                    .get("status")
                    == "duplicate",
                )
            else:
                raise ValueError("Unknown fixture stage")
            feed = await post("pending", [])
            stamp = feed.headers.get("x-mf-timestamp", "")
            sig = hmac.new(SECRET, stamp.encode() + b"." + feed.content, hashlib.sha256).hexdigest()
            check(
                "pending feed authenticates exact response bytes",
                feed.status_code == 200
                and hmac.compare_digest(sig, feed.headers.get("x-mf-signature", "")),
            )
        except Exception as exc:
            error = (
                type(exc).__name__ + ": " + str(exc)
                if isinstance(exc, AssertionError)
                else type(exc).__name__
            )
    async with async_session_maker() as db:
        check(
            "all product and variant rows, operator468 order and all other jobs unchanged",
            before == await protected(db),
        )
    print(
        json.dumps(
            {
                "fixture_order": ORDER,
                "stage": mode,
                "checks": checks,
                "failed": sum(not x["pass"] for x in checks),
                "error": error,
                "scope": "Live HTTP/SQL and native Batchivo queue service; simulated printer without hardware connection. Separate browser acceptance required.",
            }
        )
    )


asyncio.run(main())
