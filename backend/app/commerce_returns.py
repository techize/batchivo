"""Physical returns, separate from Square refunds and immutable sold quantities.

Only a shipped, provider-reconciled paid order can receive returns. Receiving
is separate from inspection and financial refunds; only inspected finite-stock goods increase stock.
Every command shares the order lock with financial and dispatch changes.
"""

import copy
import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

import httpx
from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select


class ReturnReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: int = Field(gt=0, strict=True)


class ReturnCommand(ReturnReview):
    event_id: UUID
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    line_id: int = Field(gt=0, strict=True)
    action: Literal["receive", "restock", "write_off"]
    quantity: int = Field(gt=0, le=1000, strict=True)
    actor_id: int = Field(gt=0, strict=True)
    note: str = Field(min_length=5, max_length=500)


def revision(mapping, order):
    return hashlib.sha256(
        json.dumps(
            {
                "version": mapping.version,
                "state": mapping.state,
                "snapshot": mapping.snapshot,
                "effects": mapping.effects,
                "order_state": order.status,
                "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


async def load_order(db, order_id):
    from app.commerce_bridge import TENANT, CommerceOrder, Order, reservation_order_lock

    await reservation_order_lock(db, order_id)
    mapping = await db.scalar(
        select(CommerceOrder).where(CommerceOrder.woo_order_id == order_id).with_for_update()
    )
    if not mapping:
        raise HTTPException(404, "Mapped order not found")
    order = await db.scalar(
        select(Order)
        .where(Order.id == UUID(mapping.batchivo_order_id), Order.tenant_id == TENANT)
        .with_for_update()
    )
    if not order:
        raise HTTPException(409, "Native order mapping requires reconciliation")
    return mapping, order


async def verify_refunds(mapping, order):
    from app.commerce_bridge import Event, verify_payment

    if not order.shipped_at:
        raise HTTPException(
            409,
            "Record a physical return only after dispatch; unshipped cancellations use the cancellation workflow",
        )
    if mapping.effects.get("restored"):
        raise HTTPException(
            409, "Stock was already released; return quantities require reconciliation"
        )
    refunded = mapping.effects.get("refunded_pence", 0)
    expected_status = (
        "COMPLETED"
        if refunded == 0
        else "REFUNDED"
        if refunded == mapping.snapshot["total_pence"]
        else "PARTIALLY_REFUNDED"
    )
    if order.payment_status != expected_status or mapping.state not in (
        "processing",
        "completed",
        "refunded",
    ):
        raise HTTPException(
            409, "Reconcile the completed payment and any refunds before recording returns"
        )
    try:
        payment = await verify_payment(Event.model_validate(mapping.snapshot))
    except (httpx.HTTPError, ValueError, KeyError):
        raise HTTPException(503, "Square verification unavailable; return action held") from None
    verified = {r["id"] for r in payment["_verified_refunds"]}
    if (
        verified != {r["id"] for r in mapping.effects.get("refunds", [])}
        or verified != set(payment.get("refund_ids", []))
        or payment["_verified_refunded_pence"] != mapping.effects.get("refunded_pence", 0)
        or payment.get("refunded_money", {}).get("amount", 0)
        != mapping.effects.get("refunded_pence", 0)
    ):
        raise HTTPException(
            409, "Square refund activity has changed; reconcile it before recording returns"
        )


def lines_for_review(mapping):
    ledger = mapping.effects.get("returns", {})
    finite = {(s["product_id"], s.get("variant_id")) for s in mapping.effects.get("stock", [])}
    rows = []
    seen = set()
    for line in mapping.snapshot["lines"]:
        key = str(line["line_id"])
        if key in seen:
            raise HTTPException(409, "Duplicate sold line identity requires reconciliation")
        seen.add(key)
        counts = ledger.get("lines", {}).get(key, {})
        received, restocked, written_off = (
            counts.get(k, 0) for k in ("received", "restocked", "written_off")
        )
        if not 0 <= restocked + written_off <= received <= line["quantity"]:
            raise HTTPException(409, "Return quantities require reconciliation")
        rows.append(
            {
                "line_id": line["line_id"],
                "name": line["name"],
                "sku": line["sku"],
                "option": line.get("option", ""),
                "sold": line["quantity"],
                "received": received,
                "restocked": restocked,
                "written_off": written_off,
                "awaiting_inspection": received - restocked - written_off,
                "can_restock": (line["product_id"], line.get("variant_id")) in finite,
            }
        )
    return rows


async def review_returns(order_id):
    from app.commerce_bridge import async_session_maker

    async with async_session_maker() as db, db.begin():
        mapping, order = await load_order(db, order_id)
        await verify_refunds(mapping, order)
        return {
            "order_id": order_id,
            "revision": revision(mapping, order),
            "refunded_pence": mapping.effects.get("refunded_pence", 0),
            "lines": lines_for_review(mapping),
            "history": list(mapping.effects.get("returns", {}).get("receipts", {}).values()),
        }


async def apply_return_in_transaction(db, command):
    """Caller owns the transaction; used by the HTTP handler and rollback probes."""
    from app.commerce_bridge import TENANT, Product, ProductVariant

    mapping, order = await load_order(db, command.order_id)
    digest = hashlib.sha256(command.model_dump_json().encode()).hexdigest()
    effects = copy.deepcopy(mapping.effects)
    ledger = effects.setdefault("returns", {"lines": {}, "receipts": {}})
    prior = ledger["receipts"].get(str(command.event_id))
    if prior:
        if prior["command_sha256"] != digest:
            raise HTTPException(409, "Return command identity reused with different details")
        return {
            "status": "duplicate",
            "order_id": command.order_id,
            "event_id": str(command.event_id),
            "action": command.action,
        }
    if command.note.strip() != command.note or any(ord(c) < 32 for c in command.note):
        raise HTTPException(422, "Enter a short inspection note without control characters")
    if not hmac.compare_digest(command.revision, revision(mapping, order)):
        raise HTTPException(
            409, "Return or order details changed; review the latest quantities before applying"
        )
    await verify_refunds(mapping, order)
    lines = {row["line_id"]: row for row in lines_for_review(mapping)}
    line = lines.get(command.line_id)
    if not line:
        raise HTTPException(409, "Sold line does not belong to this order")
    if len(ledger["receipts"]) >= 1000:
        raise HTTPException(409, "Return audit limit reached; operator reconciliation required")
    key = str(command.line_id)
    counts = ledger["lines"].setdefault(key, {"received": 0, "restocked": 0, "written_off": 0})
    if command.action == "receive":
        if command.quantity > line["sold"] - line["received"]:
            raise HTTPException(409, "Received quantity exceeds the remaining sold quantity")
        counts["received"] += command.quantity
    else:
        if command.quantity > line["awaiting_inspection"]:
            raise HTTPException(409, "Inspect only goods already received and awaiting inspection")
        if command.action == "restock":
            if not line["can_restock"]:
                raise HTTPException(
                    409,
                    "Print-to-order goods require a separate inventory decision; this action only restores finite stock",
                )
            sold = next(
                row for row in mapping.snapshot["lines"] if row["line_id"] == command.line_id
            )
            cls = ProductVariant if sold.get("variant_id") else Product
            stock = await db.scalar(
                select(cls)
                .where(
                    cls.id == UUID(sold.get("variant_id") or sold["product_id"]),
                    cls.tenant_id == TENANT,
                )
                .with_for_update()
            )
            if not stock or (
                sold.get("variant_id") and str(stock.product_id) != sold["product_id"]
            ):
                raise HTTPException(409, "Stock identity requires reconciliation")
            stock.units_in_stock += command.quantity
            counts["restocked"] += command.quantity
        else:
            counts["written_off"] += command.quantity
    result = {
        "status": "recorded",
        "order_id": command.order_id,
        "event_id": str(command.event_id),
        "action": command.action,
    }
    ledger["receipts"][str(command.event_id)] = {
        "command_sha256": digest,
        "event_id": str(command.event_id),
        "line_id": command.line_id,
        "action": command.action,
        "quantity": command.quantity,
        "actor_id": command.actor_id,
        "note": command.note,
        "at": datetime.now(UTC).isoformat(),
        "order_version": mapping.version,
        "refunded_pence": effects.get("refunded_pence", 0),
    }
    mapping.effects = effects
    await db.flush()
    return result


async def record_return(command):
    from app.commerce_bridge import async_session_maker

    async with async_session_maker() as db, db.begin():
        return await apply_return_in_transaction(db, command)


def install_routes(app):
    from app.commerce_bridge import signed_body, signed_response

    @app.post("/fulfilment/returns/review")
    async def review(request: Request):
        body = await signed_body(request)
        try:
            command = ReturnReview.model_validate_json(body)
            return signed_response({"ok": True, **await review_returns(command.order_id)})
        except ValueError:
            return signed_response(
                {"ok": False, "code": 422, "error": "Invalid return review details"}
            )
        except HTTPException as error:
            return signed_response(
                {"ok": False, "code": error.status_code, "error": str(error.detail)}
            )

    @app.post("/fulfilment/returns/apply")
    async def apply(request: Request):
        body = await signed_body(request)
        try:
            command = ReturnCommand.model_validate_json(body)
            return signed_response({"ok": True, **await record_return(command)})
        except ValueError:
            return signed_response({"ok": False, "code": 422, "error": "Invalid return command"})
        except HTTPException as error:
            return signed_response(
                {"ok": False, "code": error.status_code, "error": str(error.detail)}
            )
