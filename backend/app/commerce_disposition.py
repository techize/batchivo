"""Audited physical disposition of unshipped partially refunded commerce orders."""

import copy
import hashlib
import hmac
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from sqlalchemy import select

from app.commerce_returns import load_order, revision, verify_refunds


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: int = Field(gt=0, strict=True)


class Command(Review):
    event_id: UUID
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    cancelled: dict[str, StrictInt]
    actor_id: int = Field(gt=0, strict=True)
    note: str = Field(min_length=5, max_length=500)


def cancelled_quantity(effects, line):
    value = effects.get("disposition", {}).get("cancelled", {}).get(str(line["line_id"]), 0)
    if type(value) is not int or not 0 <= value <= line["quantity"]:
        raise HTTPException(409, "Cancelled quantities require reconciliation")
    return value


def remaining_quantity(effects, line):
    return line["quantity"] - cancelled_quantity(effects, line)


def refund_signature(payment):
    # Version-independent approval of exact financial facts, never aggregate money alone.
    return sorted((r["id"], r["amount_pence"]) for r in payment["_verified_refunds"])


def refund_release_valid(effects, payment):
    approval = effects.get("disposition", {}).get("approval")
    refunds = payment.get("_verified_refunds", [])
    verified_ids = {r["id"] for r in refunds}
    if not refunds:
        return not payment.get("refund_ids") and not payment.get("refunded_money", {}).get(
            "amount", 0
        )
    return bool(
        approval
        and approval["refunded_pence"]
        == payment["_verified_refunded_pence"]
        == payment.get("refunded_money", {}).get("amount", 0)
        and approval["refunds"] == [list(x) for x in refund_signature(payment)]
        and verified_ids == set(payment.get("refund_ids", []))
    )


async def review_in_transaction(db, order_id):
    from app.commerce_bridge import TENANT, PrintJob

    mapping, order = await load_order(db, order_id)
    if order.shipped_at or order.status not in ("pending", "processing"):
        raise HTTPException(409, "Only unshipped orders can receive a fulfilment decision")
    if not 0 < mapping.effects.get("refunded_pence", 0) < mapping.snapshot["total_pence"]:
        raise HTTPException(409, "Reconcile a completed partial refund before reviewing fulfilment")
    await verify_refunds(mapping, order, require_shipped=False)
    jobs = {}
    for entry in mapping.effects.get("jobs", []):
        key = str(entry["line_id"])
        if key in jobs:
            raise HTTPException(409, "Duplicate manufacturing identity")
        job = await db.scalar(
            select(PrintJob)
            .where(PrintJob.id == UUID(entry["id"]), PrintJob.tenant_id == TENANT)
            .with_for_update()
        )
        if not job:
            raise HTTPException(409, "Manufacturing job requires reconciliation")
        jobs[key] = job
    rows = []
    finite = {(e["product_id"], e.get("variant_id")) for e in mapping.effects.get("stock", [])}
    seen = set()
    for line in mapping.snapshot["lines"]:
        key = str(line["line_id"])
        if key in seen:
            raise HTTPException(409, "Duplicate sold line identity")
        seen.add(key)
        job = jobs.get(key)
        is_finite = (line["product_id"], line.get("variant_id")) in finite
        remaining = remaining_quantity(mapping.effects, line)
        if is_finite == bool(job):
            raise HTTPException(409, "Allocation or manufacturing mapping requires reconciliation")
        if job and (
            str(job.product_id) != line["product_id"] or (remaining and job.quantity != remaining)
        ):
            raise HTTPException(409, "Manufacturing quantities require reconciliation")
        rows.append(
            {
                "line_id": line["line_id"],
                "name": line["name"],
                "sku": line["sku"],
                "sold": line["quantity"],
                "cancelled": line["quantity"] - remaining,
                "remaining": remaining,
                "can_cancel": is_finite or job.status.value in ("pending", "queued"),
                "manufacturing_status": job.status.value if job else None,
            }
        )
    if set(jobs) - seen:
        raise HTTPException(409, "Unmapped manufacturing work")
    return mapping, order, jobs, rows


async def apply_in_transaction(db, command):
    from app.commerce_bridge import (
        TENANT,
        Event,
        JobStatus,
        Product,
        ProductVariant,
        verify_payment,
    )

    mapping, order = await load_order(db, command.order_id)
    digest = hashlib.sha256(command.model_dump_json().encode()).hexdigest()
    old = mapping.effects.get("disposition", {})
    prior = old.get("receipts", {}).get(str(command.event_id))
    if prior:
        if prior["command_sha256"] != digest:
            raise HTTPException(409, "Disposition identity reused with changed details")
        return {
            "status": "duplicate",
            "order_id": command.order_id,
            "event_id": str(command.event_id),
        }
    if not hmac.compare_digest(command.revision, revision(mapping, order)):
        raise HTTPException(409, "Order changed; review the latest refund and quantities")
    if command.note.strip() != command.note or any(ord(c) < 32 for c in command.note):
        raise HTTPException(422, "Enter an evidence note without control characters")
    mapping, order, jobs, rows = await review_in_transaction(db, command.order_id)
    if set(command.cancelled) != {str(r["line_id"]) for r in rows}:
        raise HTTPException(422, "Review every sold line exactly once")
    if any(not r["cancelled"] <= command.cancelled[str(r["line_id"])] <= r["sold"] for r in rows):
        raise HTTPException(
            409, "Cancelled quantities cannot be reversed or exceed sold quantities"
        )
    if all(command.cancelled[str(r["line_id"])] == r["sold"] for r in rows):
        raise HTTPException(409, "No remaining goods: complete the financial cancellation instead")
    effects = copy.deepcopy(mapping.effects)
    ledger = effects.setdefault(
        "disposition",
        {
            "cancelled": {},
            "receipts": {},
            "original_stock": copy.deepcopy(effects.get("stock", [])),
        },
    )
    if len(ledger["receipts"]) >= 1000:
        raise HTTPException(409, "Disposition audit requires operator reconciliation")
    deltas = {}
    for row in rows:
        key = str(row["line_id"])
        delta = command.cancelled[key] - row["cancelled"]
        if not delta:
            continue
        if not row["can_cancel"]:
            raise HTTPException(
                409, "Started manufacturing cannot be cancelled as unstarted demand"
            )
        line = next(x for x in mapping.snapshot["lines"] if str(x["line_id"]) == key)
        if key in jobs:
            job = jobs[key]
            remaining = row["sold"] - command.cancelled[key]
            if remaining:
                job.quantity = remaining
            else:
                job.status = JobStatus.CANCELLED
        else:
            stock_key = (line["product_id"], line.get("variant_id"))
            deltas[stock_key] = deltas.get(stock_key, 0) + delta
    for (product_id, variant_id), delta in sorted(deltas.items(), key=lambda x: str(x[0])):
        cls = ProductVariant if variant_id else Product
        stock = await db.scalar(
            select(cls)
            .where(cls.id == UUID(variant_id or product_id), cls.tenant_id == TENANT)
            .with_for_update()
        )
        if not stock or (variant_id and str(stock.product_id) != product_id):
            raise HTTPException(409, "Stock identity requires reconciliation")
        remaining_delta = delta
        for allocation in effects["stock"]:
            if (allocation["product_id"], allocation.get("variant_id")) == (product_id, variant_id):
                take = min(remaining_delta, allocation["quantity"])
                allocation["quantity"] -= take
                remaining_delta -= take
        if remaining_delta:
            raise HTTPException(409, "Outstanding stock allocation is insufficient")
        stock.units_in_stock += delta
    # Re-read the provider after constructing the decision, before committing it.
    payment = await verify_payment(Event.model_validate(mapping.snapshot))
    expected = {r["id"] for r in effects.get("refunds", [])}
    if (
        expected != set(payment.get("refund_ids", []))
        or payment["_verified_refunded_pence"] != effects["refunded_pence"]
        or payment.get("refunded_money", {}).get("amount", 0) != effects["refunded_pence"]
    ):
        raise HTTPException(409, "Refund activity changed; reconcile before release")
    ledger["cancelled"] = dict(command.cancelled)
    ledger["approval"] = {
        "refunds": [list(x) for x in refund_signature(payment)],
        "refunded_pence": effects["refunded_pence"],
    }
    ledger["receipts"][str(command.event_id)] = {
        "command_sha256": digest,
        "event_id": str(command.event_id),
        "cancelled": dict(command.cancelled),
        "actor_id": command.actor_id,
        "note": command.note,
        "at": datetime.now(UTC).isoformat(),
        "approval": copy.deepcopy(ledger["approval"]),
    }
    effects["refund_review"] = (
        "Partial refund reviewed: only remaining quantities may be manufactured and dispatched."
    )
    mapping.effects = effects
    await db.flush()
    return {"status": "recorded", "order_id": command.order_id, "event_id": str(command.event_id)}


def install_routes(app):
    import httpx

    from app.commerce_bridge import async_session_maker, signed_body, signed_response

    @app.post("/fulfilment/disposition/{action}")
    async def handle(action: str, request: Request):
        raw = await signed_body(request)
        try:
            async with async_session_maker() as db, db.begin():
                if action == "review":
                    command = Review.model_validate_json(raw)
                    mapping, order, _, rows = await review_in_transaction(db, command.order_id)
                    result = {
                        "order_id": command.order_id,
                        "revision": revision(mapping, order),
                        "lines": rows,
                        "refunded_pence": mapping.effects["refunded_pence"],
                        "history": list(
                            mapping.effects.get("disposition", {}).get("receipts", {}).values()
                        ),
                    }
                elif action == "apply":
                    result = await apply_in_transaction(db, Command.model_validate_json(raw))
                else:
                    raise HTTPException(404, "Unknown disposition action")
            return signed_response({"ok": True, **result})
        except ValueError:
            return signed_response(
                {"ok": False, "code": 422, "error": "Invalid fulfilment decision"}
            )
        except httpx.HTTPError:
            return signed_response(
                {
                    "ok": False,
                    "code": 503,
                    "error": "Payment verification unavailable; decision held",
                }
            )
        except HTTPException as error:
            return signed_response(
                {"ok": False, "code": error.status_code, "error": str(error.detail)}
            )
