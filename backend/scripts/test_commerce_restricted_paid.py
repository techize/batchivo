"""Real paid sandbox601/native start, entirely inside a rolled-back transaction."""

import asyncio
import json
from uuid import UUID
from sqlalchemy import select
from app.commerce_bridge import CommerceOrder, Order, PrintJob, RUNTIME, TENANT, async_session_maker
from app.models.print_job import JobStatus
from app.models.tenant import Tenant
from app.services.commerce_job_ownership import verify_commerce_job_work
from app.services.print_queue_service import PrintQueueService


async def main():
    if not RUNTIME.isolated:
        raise RuntimeError("Isolated test only")
    async with async_session_maker() as db:
        await db.begin()
        try:
            mapping = await db.scalar(
                select(CommerceOrder).where(CommerceOrder.woo_order_id == 601)
            )
            order = await db.get(Order, UUID(mapping.batchivo_order_id))
            assert mapping.state == "processing" and order.payment_status == "COMPLETED"
            assert (
                order.customer_email == "restricted-role-20260909@example.invalid"
                and order.tenant_id == TENANT
            )
            assert len(mapping.effects["jobs"]) == 1
            job = await db.get(PrintJob, UUID(mapping.effects["jobs"][0]["id"]))
            assert (
                job.status == JobStatus.PENDING
                and job.started_at is None
                and job.assigned_printer_id is None
            )
            assert await verify_commerce_job_work(db, job) is True
            job.status = JobStatus.QUEUED
            await db.flush()
            db.commit = db.flush
            service = PrintQueueService(db, await db.get(Tenant, TENANT))
            started = await service.start_printing(job.id)
            assert started.status == JobStatus.PRINTING and started.started_at is not None
            job_id = job.id
        finally:
            await db.rollback()
    async with async_session_maker() as db:
        job = await db.get(PrintJob, job_id)
        assert (
            job.status == JobStatus.PENDING
            and job.started_at is None
            and job.assigned_printer_id is None
        )
    print(
        json.dumps(
            {
                "order_id": 601,
                "new_job_uuid_mapping_present": True,
                "real_square_paid_verification": True,
                "native_start_allowed_inside_rollback": True,
                "persistent_job_remained_pending": True,
                "scope": "Real deployed service, Postgres and Square sandbox GET; only temporary transactional queue/start state, rolled back before other sessions could observe it. No printer assigned or physical manufacturing triggered.",
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
