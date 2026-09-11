"""Actual isolated Postgres/native service and Square readback acceptance.
All temporary stale-state/queued-state fixtures roll back. No physical printing.
"""

import asyncio
import hashlib
import json
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

import httpx
from fastapi import HTTPException
from sqlalchemy import select

from app.commerce_bridge import CommerceOrder, Order, PrintJob, RUNTIME, TENANT, async_session_maker
from app.models.print_job import JobStatus
from app.models.tenant import Tenant
from app.services.commerce_job_ownership import (
    commerce_job_mapping,
    protect_commerce_job_identity,
    verify_commerce_job_work,
)
from app.services.print_queue_service import PrintQueueService

checks = []


def check(name, condition):
    checks.append({"check": name, "pass": bool(condition)})
    if not condition:
        raise AssertionError(name)


async def state():
    async with async_session_maker() as db:
        m = await db.scalar(select(CommerceOrder).where(CommerceOrder.woo_order_id == 580))
        order = await db.get(Order, UUID(m.batchivo_order_id))
        jobs = (
            await db.scalars(
                select(PrintJob).where(
                    PrintJob.tenant_id == TENANT, PrintJob.reference.like("WOO-TEST-580:%")
                )
            )
        ).all()
        return hashlib.sha256(
            json.dumps(
                {
                    "snapshot": m.snapshot,
                    "effects": m.effects,
                    "state": m.state,
                    "order_state": order.status,
                    "payment_state": order.payment_status,
                    "jobs": [
                        (
                            str(j.id),
                            j.status.value,
                            j.reference,
                            j.notes,
                            str(j.assigned_printer_id),
                            str(j.started_at),
                        )
                        for j in jobs
                    ],
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()


async def expect_rejection(name, callback, code, contains):
    try:
        await callback()
    except HTTPException as e:
        check(name, e.status_code == code and contains in str(e.detail))
        return
    raise AssertionError(name + " was allowed")


async def main():
    if not RUNTIME.isolated:
        raise RuntimeError("Only isolated acceptance")
    baseline = await state()
    for case in [
        "refunded-start",
        "refunded-assign",
        "delete",
        "rename",
        "provider-refund",
        "provider-outage",
        "legacy",
    ]:
        async with async_session_maker() as db:
            await db.begin()
            try:
                m = await db.scalar(select(CommerceOrder).where(CommerceOrder.woo_order_id == 580))
                order = await db.get(Order, UUID(m.batchivo_order_id))
                check(
                    case + " exact synthetic fixture",
                    order.customer_email == "telegram-notification-20260909@example.invalid"
                    and order.tenant_id == TENANT,
                )
                job = await db.get(PrintJob, UUID(m.effects["jobs"][0]["id"]))
                tenant = await db.get(Tenant, TENANT)
                service = PrintQueueService(db, tenant)
                # Any unexpected native commit is only a flush in this acceptance
                # transaction, so the finally rollback preserves the fixture.
                db.commit = db.flush
                if case == "refunded-start":
                    job.status = JobStatus.QUEUED
                    await db.flush()
                    await expect_rejection(
                        "native start blocks local refund",
                        lambda: service.start_printing(job.id),
                        409,
                        "payment or refund",
                    )
                elif case == "refunded-assign":
                    await expect_rejection(
                        "native assignment blocks refunded job",
                        lambda: service.assign_to_printer(job.id, uuid4()),
                        409,
                        "payment or refund",
                    )
                elif case == "delete":
                    await expect_rejection(
                        "native delete preserves commerce history",
                        lambda: service.delete_job(job.id),
                        409,
                        "identity",
                    )
                elif case == "rename":
                    job.reference = "renamed-inside-rollback"
                    await db.flush()
                    check(
                        "UUID retains ownership after reference changes",
                        (await commerce_job_mapping(db, job))["woo_order_id"] == 580,
                    )
                    await expect_rejection(
                        "mapped identity edits rejected",
                        lambda: protect_commerce_job_identity(db, job, {"reference": "changed"}),
                        409,
                        "identity",
                    )
                elif case in ["provider-refund", "provider-outage"]:
                    # Emulate delayed Woo/Batchivo notification processing. Square
                    # remains authoritative and has a real completed sandbox refund.
                    m.state = "processing"
                    m.snapshot = {
                        **m.snapshot,
                        "state": "processing",
                        "refunded_pence": 0,
                        "refund_ids": [],
                    }
                    order.payment_status = "COMPLETED"
                    job.status = JobStatus.QUEUED
                    await db.flush()
                    if case == "provider-refund":
                        await expect_rejection(
                            "real Square refund blocks start despite stale local state",
                            lambda: service.start_printing(job.id),
                            409,
                            "Square refund activity",
                        )
                    else:
                        with patch(
                            "app.commerce_bridge.verify_payment",
                            AsyncMock(side_effect=httpx.ConnectError("controlled outage")),
                        ):
                            await expect_rejection(
                                "provider transport outage holds native start",
                                lambda: service.start_printing(job.id),
                                503,
                                "manufacturing held",
                            )
                    check(
                        case + " job remained queued",
                        job.status == JobStatus.QUEUED and job.started_at is None,
                    )
                else:
                    legacy = SimpleNamespace(
                        id=uuid4(), tenant_id=TENANT, reference="MANUAL-ACCEPTANCE"
                    )
                    check(
                        "unmapped manual jobs retain native ownership",
                        await verify_commerce_job_work(db, legacy) is False,
                    )
            finally:
                await db.rollback()
    check("fixture state unchanged after every rollback", baseline == await state())
    print(
        json.dumps(
            {
                "checks": checks,
                "failed": 0,
                "scope": "Actual deployed native service, PostgreSQL ownership mappings and real Square sandbox refunded payment580. Delayed local state and provider transport exception are controlled rollback fixtures. No real manufacturing or customer effects.",
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
