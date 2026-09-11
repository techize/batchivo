"""Real PostgreSQL dispatch transactions, nested under an outer rollback."""

import asyncio
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
                    select(bridge.CommerceOrder).where(bridge.CommerceOrder.woo_order_id == 605)
                )
                order_id = UUID(mapping.batchivo_order_id)
                order = await db.get(bridge.Order, order_id)
                from app.commerce_disposition import review_in_transaction
                from app.services.commerce_job_ownership import verify_commerce_job_work

                mapping, order, jobs, _rows = await review_in_transaction(db, 605)
                job = next(iter(jobs.values()))
                check(
                    "Browser decision retained one variant",
                    job.quantity == 1 and job.status == bridge.JobStatus.PENDING,
                )
                check(
                    "Native manufacturing assignment accepts exact reviewed refund",
                    await verify_commerce_job_work(db, job),
                )
                job.status = bridge.JobStatus.QUEUED
                await db.flush()
                check(
                    "Native manufacturing start accepts remaining quantity",
                    await verify_commerce_job_work(db, job, starting=True),
                )
                await db.commit()
            command = bridge.DispatchCommand(
                event_id=uuid4(),
                order_id=605,
                state="shipped",
                tracking_number="SIMULATED-ROLLBACK-605",
            )

            async def apply(cmd):
                raw = json.dumps(cmd.model_dump(mode="json"), sort_keys=True).encode()
                return await bridge.record_dispatch(cmd, hashlib.sha256(raw).hexdigest())

            try:
                await apply(command)
            except HTTPException as error:
                check(
                    "Unfinished remaining manufacturing blocks dispatch", error.status_code == 409
                )
            else:
                check("Unfinished remaining manufacturing blocks dispatch", False)
            async with bridge.async_session_maker() as db:
                job = await db.get(bridge.PrintJob, job.id)
                job.status = bridge.JobStatus.COMPLETED
                await db.commit()
            check(
                "Completed remaining goods can dispatch after partial refund",
                (await apply(command))["status"] == "recorded",
            )
            check(
                "Dispatch exact replay does not duplicate shipment",
                (await apply(command))["status"] == "duplicate",
            )
            async with bridge.async_session_maker() as db:
                mapping = await db.scalar(
                    select(bridge.CommerceOrder).where(bridge.CommerceOrder.woo_order_id == 605)
                )
                order = await db.get(bridge.Order, UUID(mapping.batchivo_order_id))
                check(
                    "Shipment retains original sale and partial-refund money",
                    order.payment_status == "PARTIALLY_REFUNDED"
                    and mapping.snapshot["total_pence"] == 3397
                    and mapping.effects["refunded_pence"] == 999
                    and order.status == "shipped",
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
                "scope": "Actual restricted PostgreSQL transactions/savepoints with outer rollback. Actual Square sandbox read-only payment/refund verification; no payment writes or customer messages. Manufacturing completion is simulated only inside rollback; persisted browser decision is real.",
            }
        )
    )


asyncio.run(main())
