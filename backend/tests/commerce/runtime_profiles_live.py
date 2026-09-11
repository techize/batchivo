"""Read-only real sandbox verification after the runtime-profile rollout."""

import asyncio
import json
import os
from fastapi import HTTPException
from sqlalchemy import select, text
from app.commerce_bridge import (
    RUNTIME,
    CommerceOrder,
    Event,
    PrintJob,
    TENANT,
    async_session_maker,
    verify_payment,
    CommerceSession,
)


async def main():
    checks = []

    def check(name, value):
        checks.append({"check": name, "pass": bool(value)})

    check("running process remains isolated", RUNTIME.isolated)
    async with async_session_maker() as db:
        check(
            "bridge transaction receives fixed tenant context",
            await db.scalar(text("SELECT current_setting('app.current_tenant_id',true)"))
            == str(TENANT),
        )
        for oid in [468, 557, 571]:
            mapping = await db.scalar(
                select(CommerceOrder).where(CommerceOrder.woo_order_id == oid)
            )
            event = Event.model_validate(mapping.snapshot)
            payment = await verify_payment(event)
            check(
                f"{oid} actual Square sandbox payment and location verified",
                payment["status"] == "COMPLETED"
                and payment["amount_money"]["amount"] == event.total_pence,
            )
            check(
                f"{oid} provider order reference matches Woo identity",
                payment.get("reference_id") == str(oid),
            )
            check(
                f"{oid} provider reservation note matches immutable hold",
                not event.reservation_id
                or payment.get("note", "").startswith(
                    "[MF-RESERVATION:" + str(event.reservation_id) + "] "
                ),
            )
            refs = (
                await db.scalars(
                    select(PrintJob.reference).where(
                        PrintJob.tenant_id == TENANT,
                        PrintJob.reference.like(RUNTIME.order_reference(oid) + ":%"),
                    )
                )
            ).all()
            check(
                f"{oid} existing test manufacturing references retained",
                bool(refs)
                and set(refs) == {RUNTIME.job_reference(oid, line.line_id) for line in event.lines},
            )
        from uuid import uuid4

        for name, updates in [
            ("order reference", {"order_id": event.order_id + 100000}),
            ("reservation identity", {"reservation_id": uuid4()}),
        ]:
            rejected = False
            try:
                await verify_payment(event.model_copy(update=updates))
            except HTTPException as e:
                rejected = e.status_code == 409
            check("real provider payment rejected for mismatched " + name, rejected)
        original = os.environ[RUNTIME.location_environment_key]
        try:
            os.environ[RUNTIME.location_environment_key] = "WRONG-ISOLATED-FIXTURE-LOCATION"
            rejected = False
            try:
                await verify_payment(event)
            except HTTPException as e:
                rejected = e.status_code == 409
            check("real provider payment rejected for a different configured location", rejected)
        finally:
            os.environ[RUNTIME.location_environment_key] = original
    from app.database import async_session_maker as native_sessions

    async with native_sessions() as native:
        check(
            "native sessions retain independent session class",
            not isinstance(native.sync_session, CommerceSession),
        )
        check(
            "bridge tenant does not leak into native transactions",
            not await native.scalar(text("SELECT current_setting('app.current_tenant_id',true)")),
        )
    print(
        json.dumps(
            {
                "checks": checks,
                "failed": sum(not c["pass"] for c in checks),
                "scope": "Read-only actual Square sandbox GET verification and native reference lookup; no charges, refunds, orders, stock or configuration changes.",
            }
        )
    )
    if any(not c["pass"] for c in checks):
        raise SystemExit(1)


asyncio.run(main())
