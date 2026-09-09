"""Preserve commerce manufacturing identity and check payment before new work.

Job UUIDs in the durable commerce effects ledger are authoritative. References
only detect missing mappings; removing a reference cannot relinquish ownership.
Already started/completed work remains physical history when a refund arrives.
"""

import json
import os

from fastapi import HTTPException
from sqlalchemy import text

from app.commerce_runtime import CommerceRuntime


async def commerce_job_mapping(db, job):
    if db.bind.dialect.name == "postgresql":
        exists = await db.scalar(text("SELECT to_regclass('public.commerce_orders')"))
        if exists:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT c.woo_order_id, c.state, c.snapshot, c.effects, o.payment_status "
                            "FROM commerce_orders c JOIN orders o ON o.id=c.batchivo_order_id::uuid "
                            "WHERE o.tenant_id=:tenant AND c.effects @> CAST(:identity AS jsonb)"
                        ),
                        {
                            "tenant": job.tenant_id,
                            "identity": json.dumps({"jobs": [{"id": str(job.id)}]}),
                        },
                    )
                )
                .mappings()
                .all()
            )
            if len(rows) > 1:
                raise HTTPException(409, "Commerce manufacturing ownership requires reconciliation")
            if rows:
                return dict(rows[0])
    if (job.reference or "").startswith("WOO-"):
        raise HTTPException(409, "Commerce manufacturing mapping requires reconciliation")
    return None


async def protect_commerce_job_identity(db, job, changes=None, deleting=False):
    mapping = await commerce_job_mapping(db, job)
    if mapping is not None and (
        deleting
        or set(changes or {}) & {"reference", "notes", "product_id", "quantity", "model_id"}
    ):
        raise HTTPException(
            409,
            "Commerce job identity and variant details are preserved; reconcile through the commerce workflow",
        )


async def verify_commerce_job_work(db, job, starting=False):
    mapping = await commerce_job_mapping(db, job)
    if mapping is None:
        return False
    try:
        runtime = CommerceRuntime.from_environment(os.environ)
    except RuntimeError:
        raise HTTPException(409, "Commerce manufacturing requires an activated release") from None
    from app.commerce_bridge import TENANT, Event, reservation_order_lock, verify_payment

    if job.tenant_id != TENANT:
        raise HTTPException(404, "Job not found")
    # Same order lock as refunds/dispatch, then refresh the job under a row lock.
    await reservation_order_lock(db, mapping["woo_order_id"])
    await db.refresh(job, with_for_update=True)
    mapping = await commerce_job_mapping(db, job)
    if mapping is None:
        raise HTTPException(409, "Commerce manufacturing mapping changed")
    from app.models.print_job import JobStatus

    if mapping["state"] not in ("processing", "completed") or mapping["payment_status"] not in (
        "COMPLETED",
        "PARTIALLY_REFUNDED",
    ):
        raise HTTPException(409, "Commerce payment or refund state prevents new manufacturing")
    allowed = (
        (JobStatus.QUEUED,) if starting else (JobStatus.PENDING, JobStatus.QUEUED, JobStatus.FAILED)
    )
    if job.status not in allowed:
        raise HTTPException(409, "Commerce job cannot be restarted from its current state")
    identities = [
        entry for entry in mapping["effects"].get("jobs", []) if entry["id"] == str(job.id)
    ]
    if len(identities) != 1:
        raise HTTPException(409, "Commerce manufacturing identity requires reconciliation")
    identity = identities[0]
    lines = [
        line
        for line in mapping["snapshot"]["lines"]
        if str(line["line_id"]) == str(identity["line_id"])
    ]
    if len(lines) != 1:
        raise HTTPException(409, "Commerce manufacturing line requires reconciliation")
    line = lines[0]
    from app.commerce_disposition import refund_release_valid, remaining_quantity

    remaining = remaining_quantity(mapping["effects"], line)
    if remaining < 1:
        raise HTTPException(409, "This manufacturing line was cancelled")
    if (
        str(job.product_id) != line["product_id"]
        or job.quantity != remaining
        or job.reference != runtime.job_reference(mapping["woo_order_id"], line["line_id"])
    ):
        raise HTTPException(
            409, "Commerce manufacturing product or quantity requires reconciliation"
        )
    import httpx

    try:
        payment = await verify_payment(Event.model_validate(mapping["snapshot"]))
    except (httpx.HTTPError, ValueError, KeyError):
        raise HTTPException(503, "Payment verification unavailable; manufacturing held") from None
    if not refund_release_valid(mapping["effects"], payment):
        raise HTTPException(409, "Square refund activity requires review before new manufacturing")
    return True
