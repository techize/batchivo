"""WooCommerce bridge with explicit isolated and separately activated production profiles."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import hmac
import json
import os
import sys
import time
from uuid import UUID, uuid4
from typing import Literal
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import (
    event,
    inspect,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    and_,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session, Mapped, mapped_column, raiseload
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.commerce_runtime import CommerceRuntime

RUNTIME = CommerceRuntime.from_environment(os.environ)
from app.database import Base, engine as native_engine
from app.services.commerce_database import commerce_engine, verify_commerce_role
from app.services.commerce_sales_channel import commerce_sales_channel

engine = commerce_engine(RUNTIME, os.environ, native_engine)
from app.models import Product, ProductVariant, Tenant, Order, OrderItem, PrintJob, JobStatus
from app.models.base import UUIDMixin, TimestampMixin

TENANT = UUID(os.environ["COMMERCE_TENANT_ID"])
SECRET = os.environ["COMMERCE_BRIDGE_SECRET"].encode()
# The actual engine target must agree with the configuration guard, including RLS URLs.
CommerceRuntime.from_environment(
    {
        **os.environ,
        "DATABASE_URL": engine.url.render_as_string(hide_password=False),
        "RLS_ENABLED": "false",
    }
)


class CommerceSession(Session):
    pass


@event.listens_for(CommerceSession, "do_orm_execute")
def commerce_explicit_relationships(state):
    # Catalogue ORM defaults eagerly load pricing, designers and other native
    # data that payment/stock writes do not use. Only explicit relationships are
    # available in commerce sessions; native application sessions are unchanged.
    if state.is_select:
        state.statement = state.statement.options(raiseload("*"))


@event.listens_for(CommerceSession, "after_begin")
def commerce_tenant_context(session, transaction, connection):
    if os.environ.get("COMMERCE_DATABASE_URL") or not RUNTIME.isolated:
        verify_commerce_role(connection)
    connection.execute(
        text("SELECT set_config('app.current_tenant_id',:tenant,true)"), {"tenant": str(TENANT)}
    )


# Only bridge sessions get this fixed tenant; native application sessions retain their own context.
async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False, autoflush=False, sync_session_class=CommerceSession
)


class CommerceReceipt(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "commerce_receipts"
    event_id: Mapped[str] = mapped_column(String(64), unique=True)
    body_sha256: Mapped[str] = mapped_column(String(64))
    woo_order_id: Mapped[int] = mapped_column(Integer, index=True)
    outcome: Mapped[str] = mapped_column(String(32))


class CommerceOrder(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "commerce_orders"
    woo_order_id: Mapped[int] = mapped_column(Integer, unique=True)
    batchivo_order_id: Mapped[str] = mapped_column(String(36))
    version: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(32))
    snapshot: Mapped[dict] = mapped_column(JSONB)
    effects: Mapped[dict] = mapped_column(JSONB, default=dict)


class CommerceFulfilmentEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "commerce_fulfilment_events"
    __table_args__ = (UniqueConstraint("woo_order_id", "version"),)
    event_id: Mapped[str] = mapped_column(String(36), unique=True)
    command_sha256: Mapped[str] = mapped_column(String(64))
    woo_order_id: Mapped[int] = mapped_column(Integer, index=True)
    version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(16), default="pending", index=True)


class DispatchCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: UUID
    order_id: int = Field(gt=0)
    state: Literal["shipped", "delivered"]
    tracking_number: str = Field(default="", max_length=100)
    tracking_url: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def valid(self):
        if any(ord(c) < 32 for c in self.tracking_number + self.tracking_url):
            raise ValueError("Invalid tracking characters")
        if self.tracking_url:
            value = urlsplit(self.tracking_url)
            if value.scheme != "https" or not value.hostname or value.username or value.password:
                raise ValueError("Tracking links must be HTTPS without embedded credentials")
        return self


payment_identity_index = Index(
    "commerce_orders_payment_unique", CommerceOrder.snapshot["payment_id"].astext, unique=True
)


class Line(BaseModel):
    model_config = ConfigDict(extra="forbid")
    line_id: int = Field(gt=0)
    product_id: UUID
    variant_id: UUID | None = None
    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    option: str = ""
    quantity: int = Field(gt=0, le=1000)
    total_pence: int = Field(ge=0)


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: UUID
    order_id: int = Field(gt=0)
    version: int = Field(gt=0)
    state: str
    payment_id: str = Field(min_length=1, max_length=192)
    reservation_id: UUID | None = None
    refunded_pence: int | None = Field(default=None, ge=0)
    refund_ids: list[str] = Field(default_factory=list, max_length=100)
    currency: str = "GBP"
    subtotal_pence: int = Field(ge=0)
    shipping_pence: int = Field(ge=0)
    discount_pence: int = Field(ge=0)
    total_pence: int = Field(ge=0)
    lines: list[Line] = Field(min_length=1, max_length=100)
    customer: dict
    shipping: dict

    @model_validator(mode="after")
    def valid(self):
        if self.currency != "GBP" or self.state not in [
            "processing",
            "completed",
            "cancelled",
            "refunded",
        ]:
            raise ValueError("Unsupported currency or state")
        if self.refunded_pence is not None and (
            self.refunded_pence > self.total_pence
            or (self.state == "refunded" and self.refunded_pence != self.total_pence)
        ):
            raise ValueError("Invalid cumulative refund amount")
        if len(set(self.refund_ids)) != len(self.refund_ids) or any(
            not v or len(v) > 192 for v in self.refund_ids
        ):
            raise ValueError("Invalid refund identities")
        if sum(x.total_pence for x in self.lines) + self.shipping_pence != self.total_pence:
            raise ValueError("Line/shipping totals do not reconcile")
        if not RUNTIME.isolated:
            for fields, required in [
                (self.customer, ["email", "name"]),
                (self.shipping, ["address_1", "city", "postcode"]),
            ]:
                if any(
                    not isinstance(fields.get(key), str) or not fields[key].strip()
                    for key in required
                ):
                    raise ValueError("Production orders require customer and delivery details")
            if "@" not in self.customer["email"] or self.shipping.get("country") != "GB":
                raise ValueError(
                    "Production orders require a valid email and supported delivery country"
                )
        return self


async def enrich_job_options(db, event: Event):
    """Fill absent display labels from the validated variant; never change work or stock."""
    changed = 0
    for line in event.lines:
        if not line.variant_id:
            continue
        variant = await db.get(ProductVariant, line.variant_id)
        if (
            not variant
            or variant.tenant_id != TENANT
            or variant.product_id != line.product_id
            or variant.sku != line.sku
        ):
            raise HTTPException(409, "Variant label reconciliation requires a valid mapping")
        jobs = (
            await db.scalars(
                select(PrintJob)
                .where(
                    PrintJob.tenant_id == TENANT,
                    PrintJob.reference == RUNTIME.job_reference(event.order_id, line.line_id),
                )
                .with_for_update()
            )
        ).all()
        for job in jobs:
            notes = json.loads(job.notes or "{}")
            if not notes.get("option"):
                if (
                    job.product_id != line.product_id
                    or notes.get("variant_id") != str(line.variant_id)
                    or notes.get("sku") != line.sku
                ):
                    raise HTTPException(409, "Manufacturing label mapping mismatch")
                notes["option"] = variant.size
                notes["option_source"] = "validated_batchivo_variant"
                job.notes = json.dumps(notes)
                changed += 1
    return changed


class CommerceReservation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "commerce_reservations"
    reservation_id: Mapped[str] = mapped_column(String(36), unique=True)
    woo_order_id: Mapped[int] = mapped_column(Integer, index=True)
    state: Mapped[str] = mapped_column(String(32), index=True)
    snapshot: Mapped[dict] = mapped_column(JSONB)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reservation_id: UUID
    order_id: int = Field(gt=0)
    total_pence: int = Field(ge=0)
    currency: str = "GBP"
    lines: list[Line] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def valid(self):
        if self.currency != "GBP" or len({line.line_id for line in self.lines}) != len(self.lines):
            raise ValueError("Invalid reservation currency or duplicate line IDs")
        return self


class ReservationAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reservation_id: UUID
    order_id: int = Field(gt=0)
    action: str
    decline_code: str = ""


async def signed_body(request):
    body = await request.body()
    if len(body) > 256000:
        raise HTTPException(413, "Payload too large")
    stamp = request.headers.get("x-mf-timestamp", "")
    if not stamp.isdigit() or abs(time.time() - int(stamp)) > 300:
        raise HTTPException(401, "Expired event signature")
    expected = hmac.new(SECRET, stamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get("x-mf-signature", "")):
        raise HTTPException(401, "Invalid event signature")
    return body


def signed_response(data):
    body = json.dumps(data, separators=(",", ":"), sort_keys=True)
    stamp = str(int(time.time()))
    signature = hmac.new(SECRET, (stamp + "." + body).encode(), hashlib.sha256).hexdigest()
    return Response(
        content=body,
        media_type="application/json",
        headers={"X-MF-Timestamp": stamp, "X-MF-Signature": signature},
    )


async def reservation_order_lock(db, order_id):
    await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": order_id})


def reservation_identity(snapshot):
    return (
        snapshot["order_id"],
        snapshot["currency"],
        snapshot["total_pence"],
        sorted(
            (
                str(x["product_id"]),
                str(x.get("variant_id")),
                x["sku"],
                x["quantity"],
                x["total_pence"],
                x["line_id"],
            )
            for x in snapshot["lines"]
        ),
    )


async def locked_reservation_stock(db, lines):
    quantities = {}
    stock_rows = {}
    # Stable parent/variant order serializes overlaps, including duplicate basket lines.
    for line in sorted(lines, key=lambda x: (str(x.product_id), str(x.variant_id))):
        product = await db.scalar(
            select(Product)
            .where(Product.id == line.product_id, Product.tenant_id == TENANT)
            .with_for_update()
        )
        if not product or not product.is_active:
            raise HTTPException(409, "Unknown or inactive mapped product")
        variant = None
        if line.variant_id:
            variant = await db.scalar(
                select(ProductVariant)
                .where(
                    ProductVariant.id == line.variant_id,
                    ProductVariant.product_id == product.id,
                    ProductVariant.tenant_id == TENANT,
                    ProductVariant.is_active.is_(True),
                )
                .with_for_update()
            )
            if not variant:
                raise HTTPException(409, "Invalid mapped variant")
        stock = variant or product
        if line.sku != stock.sku:
            raise HTTPException(409, "SKU does not match source mapping")
        pto = (
            variant.fulfilment_type in ["print_to_order", "made_to_order"]
            if variant
            else product.print_to_order
        )
        if not pto:
            key = (str(product.id), str(variant.id) if variant else None)
            quantities[key] = quantities.get(key, 0) + line.quantity
            stock_rows[key] = stock
    return quantities, stock_rows


@asynccontextmanager
async def commerce_lifespan(app):
    async with engine.begin() as conn:
        if os.environ.get("COMMERCE_DATABASE_URL") or not RUNTIME.isolated:
            await conn.run_sync(verify_commerce_role)
        if RUNTIME.isolated:
            await conn.run_sync(
                lambda sync: CommerceReservation.__table__.create(sync, checkfirst=True)
            )
            await conn.run_sync(
                lambda sync: CommerceFulfilmentEvent.__table__.create(sync, checkfirst=True)
            )
        else:
            required = [
                "commerce_receipts",
                "commerce_orders",
                "commerce_fulfilment_events",
                "commerce_reservations",
            ]
            present = await conn.run_sync(
                lambda sync: all(inspect(sync).has_table(name) for name in required)
            )
            if not present:
                raise RuntimeError(
                    "Production commerce migration must be applied before activation"
                )
    yield


app = FastAPI(
    title="Batchivo commerce integration", docs_url=None, redoc_url=None, lifespan=commerce_lifespan
)


@app.post("/reservations")
async def reserve(request: Request):
    body = await signed_body(request)
    try:
        data = ReservationRequest.model_validate_json(body)
    except ValueError:
        raise HTTPException(422, "Invalid reservation")
    snapshot = data.model_dump(mode="json")
    now = datetime.now(timezone.utc)
    async with async_session_maker() as db, db.begin():
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,2))"),
            {"key": str(data.reservation_id)},
        )
        await reservation_order_lock(db, data.order_id)
        prior = await db.scalar(
            select(CommerceReservation)
            .where(CommerceReservation.reservation_id == str(data.reservation_id))
            .with_for_update()
        )
        if prior:
            if reservation_identity(prior.snapshot) != reservation_identity(snapshot):
                raise HTTPException(409, "Reservation identity cannot be changed")
            if prior.state == "held" and prior.expires_at <= now:
                raise HTTPException(409, "Reservation expired; use a new attempt")
            if prior.state not in ["held", "payment_pending"]:
                raise HTTPException(409, "Reservation is terminal")
            return {
                "reservation_id": prior.reservation_id,
                "state": prior.state,
                "expires_at": prior.expires_at.isoformat(),
            }
        existing = await db.scalar(
            select(CommerceReservation).where(
                CommerceReservation.woo_order_id == data.order_id,
                or_(
                    CommerceReservation.state.in_(["payment_pending", "committed"]),
                    and_(CommerceReservation.state == "held", CommerceReservation.expires_at > now),
                ),
            )
        )
        if existing:
            raise HTTPException(409, "Order already has an active reservation")
        needed, stocks = await locked_reservation_stock(db, data.lines)
        active = (
            await db.scalars(
                select(CommerceReservation).where(
                    or_(
                        CommerceReservation.state == "payment_pending",
                        and_(
                            CommerceReservation.state == "held",
                            CommerceReservation.expires_at > now,
                        ),
                    )
                )
            )
        ).all()
        reserved = {}
        for row in active:
            if row.state == "held" and row.expires_at <= now:
                continue
            for line in row.snapshot["lines"]:
                key = (line["product_id"], line.get("variant_id"))
                reserved[key] = reserved.get(key, 0) + line["quantity"]
        if any(
            stocks[key].units_in_stock - reserved.get(key, 0) < qty for key, qty in needed.items()
        ):
            raise HTTPException(409, "Insufficient available stock")
        row = CommerceReservation(
            reservation_id=str(data.reservation_id),
            woo_order_id=data.order_id,
            state="held",
            snapshot=snapshot,
            expires_at=now + timedelta(minutes=15),
        )
        db.add(row)
    return {
        "reservation_id": row.reservation_id,
        "state": row.state,
        "expires_at": row.expires_at.isoformat(),
    }


@app.post("/reservations/action")
async def reservation_action(request: Request):
    body = await signed_body(request)
    try:
        data = ReservationAction.model_validate_json(body)
    except ValueError:
        raise HTTPException(422, "Invalid reservation action")
    if data.action not in ["begin_payment", "release", "payment_declined"]:
        raise HTTPException(422, "Unknown reservation action")
    async with async_session_maker() as db, db.begin():
        await reservation_order_lock(db, data.order_id)
        row = await db.scalar(
            select(CommerceReservation)
            .where(
                CommerceReservation.reservation_id == str(data.reservation_id),
                CommerceReservation.woo_order_id == data.order_id,
            )
            .with_for_update()
        )
        if not row:
            raise HTTPException(404, "Reservation not found")
        if data.action == "begin_payment":
            # Lock the same inventory rows as a competing reservation before validating expiry.
            await locked_reservation_stock(
                db, ReservationRequest.model_validate(row.snapshot).lines
            )
            if row.state == "held" and row.expires_at > datetime.now(timezone.utc):
                row.state = "payment_pending"
            elif row.state != "payment_pending":
                raise HTTPException(409, "Reservation cannot start payment")
        elif data.action == "payment_declined":
            # Authenticated checkout reports a definitive response for this exact attempt.
            if data.decline_code not in [
                "GENERIC_DECLINE",
                "CARD_DECLINED",
                "VERIFY_CVV_FAILURE",
                "VERIFY_AVS_FAILURE",
            ]:
                raise HTTPException(422, "Not a definitive supported decline")
            if row.state == "payment_pending":
                row.state = "declined"
            elif row.state != "declined":
                raise HTTPException(409, "Reservation cannot accept a decline")
        else:
            if row.state == "held":
                row.state = "released"
            elif row.state != "released":
                raise HTTPException(409, "Payment may be in flight; reconcile before release")
    return {"reservation_id": row.reservation_id, "state": row.state}


class StockKey(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: UUID
    variant_id: UUID | None = None


class StockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[StockKey] = Field(min_length=1, max_length=100)


@app.post("/stock")
async def stock_snapshot(request: Request):
    body = await signed_body(request)
    try:
        data = StockRequest.model_validate_json(body)
    except ValueError:
        raise HTTPException(422, "Invalid stock request")
    now = datetime.now(timezone.utc)
    items = []
    async with async_session_maker() as db:
        holds = (
            await db.scalars(
                select(CommerceReservation).where(
                    or_(
                        CommerceReservation.state == "payment_pending",
                        and_(
                            CommerceReservation.state == "held",
                            CommerceReservation.expires_at > now,
                        ),
                    )
                )
            )
        ).all()
        reserved = {}
        for row in holds:
            for line in row.snapshot["lines"]:
                key = (line["product_id"], line.get("variant_id"))
                reserved[key] = reserved.get(key, 0) + line["quantity"]
        for key in data.items:
            product = await db.scalar(
                select(Product).where(Product.id == key.product_id, Product.tenant_id == TENANT)
            )
            if not product:
                raise HTTPException(409, "Stock mapping not found")
            variant = None
            if key.variant_id:
                variant = await db.scalar(
                    select(ProductVariant).where(
                        ProductVariant.id == key.variant_id,
                        ProductVariant.product_id == product.id,
                        ProductVariant.tenant_id == TENANT,
                    )
                )
                if not variant:
                    raise HTTPException(409, "Variant mapping not found")
            stock = variant or product
            pto = (
                variant.fulfilment_type in ["print_to_order", "made_to_order"]
                if variant
                else product.print_to_order
            )
            active = product.is_active and (variant.is_active if variant else True)
            quantity = (
                max(
                    0,
                    stock.units_in_stock
                    - reserved.get(
                        (str(key.product_id), str(key.variant_id) if key.variant_id else None), 0
                    ),
                )
                if active
                else 0
            )
            items.append(
                {
                    "product_id": str(key.product_id),
                    "variant_id": str(key.variant_id) if key.variant_id else None,
                    "available": quantity,
                    "print_to_order": pto,
                }
            )
    return {"items": items}


@app.post("/fulfilment/dispatch")
async def dispatch(request: Request):
    body = await signed_body(request)
    try:
        command = DispatchCommand.model_validate_json(body)
    except ValueError:
        raise HTTPException(422, "Invalid dispatch command")
    return await record_dispatch(command, hashlib.sha256(body).hexdigest())


async def record_dispatch(command: DispatchCommand, digest: str):
    """Single durable dispatch path for signed integration and native operator actions."""
    async with async_session_maker() as db, db.begin():
        await db.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {
                "key": -int.from_bytes(
                    hashlib.sha256(str(command.event_id).encode()).digest()[:7], "big"
                )
                - 1
            },
        )
        await reservation_order_lock(db, command.order_id)
        prior = await db.scalar(
            select(CommerceFulfilmentEvent).where(
                CommerceFulfilmentEvent.event_id == str(command.event_id)
            )
        )
        if prior:
            if prior.command_sha256 != digest:
                raise HTTPException(409, "Dispatch identity reused with different data")
            return {"status": "duplicate", "event_id": prior.event_id, "version": prior.version}
        mapping = await db.scalar(
            select(CommerceOrder)
            .where(CommerceOrder.woo_order_id == command.order_id)
            .with_for_update()
        )
        if not mapping:
            raise HTTPException(404, "Mapped paid order not found")
        order = await db.scalar(
            select(Order)
            .where(Order.id == UUID(mapping.batchivo_order_id), Order.tenant_id == TENANT)
            .with_for_update()
        )
        if not order:
            raise HTTPException(409, "Mapped order is unavailable")
        previous = await db.scalar(
            select(CommerceFulfilmentEvent)
            .where(CommerceFulfilmentEvent.woo_order_id == command.order_id)
            .order_by(CommerceFulfilmentEvent.version.desc())
            .limit(1)
        )
        if command.state == "shipped":
            from app.commerce_disposition import remaining_quantity, refund_release_valid

            if order.payment_status not in ["COMPLETED", "PARTIALLY_REFUNDED"] or mapping.state in [
                "cancelled",
                "refunded",
            ]:
                raise HTTPException(409, "Order cannot be dispatched")
            if order.status not in ["pending", "processing"] or order.shipped_at:
                raise HTTPException(409, "Order has already been dispatched or is terminal")
            jobs = (
                await db.scalars(
                    select(PrintJob)
                    .where(
                        PrintJob.tenant_id == TENANT,
                        PrintJob.reference.like(RUNTIME.order_reference(command.order_id) + ":%"),
                    )
                    .with_for_update()
                )
            ).all()
            finite = {
                (effect["product_id"], effect["variant_id"])
                for effect in mapping.effects.get("stock", [])
            }
            expected = {
                RUNTIME.job_reference(command.order_id, line["line_id"]): line
                for line in mapping.snapshot["lines"]
                if (line["product_id"], line.get("variant_id")) not in finite
            }
            if len(jobs) != len(expected) or {job.reference for job in jobs} != set(expected):
                raise HTTPException(409, "Manufacturing job mappings require reconciliation")
            if any(
                job.product_id != UUID(expected[job.reference]["product_id"])
                or (
                    remaining_quantity(mapping.effects, expected[job.reference])
                    and job.quantity != remaining_quantity(mapping.effects, expected[job.reference])
                )
                for job in jobs
            ):
                raise HTTPException(409, "Manufacturing quantities require reconciliation")
            if any(
                job.status
                != (
                    JobStatus.COMPLETED
                    if remaining_quantity(mapping.effects, expected[job.reference])
                    else JobStatus.CANCELLED
                )
                for job in jobs
            ):
                raise HTTPException(409, "Manufacturing jobs must be completed before dispatch")
            try:
                payment = await verify_payment(Event.model_validate(mapping.snapshot))
            except httpx.HTTPError:
                raise HTTPException(503, "Payment verification unavailable; dispatch not recorded")
            if not refund_release_valid(mapping.effects, payment):
                raise HTTPException(409, "Refund activity requires review before dispatch")
            order.shipped_at = datetime.now(timezone.utc)
            order.tracking_number = command.tracking_number or None
            order.tracking_url = command.tracking_url or None
            # Commerce has already committed stock/payment effects. Never deduct again here.
            if not order.fulfilled_at:
                order.fulfilled_at = order.shipped_at
        else:
            # Delivery is a physical fact about an existing shipment. A later
            # refund must not erase or block it, or reopen the financial order.
            if mapping.state == "cancelled" or order.payment_status not in [
                "COMPLETED",
                "PARTIALLY_REFUNDED",
                "REFUNDED",
            ]:
                raise HTTPException(409, "Order requires reconciliation before delivery")
            if (
                order.status != "shipped"
                or not order.shipped_at
                or order.delivered_at
                or not previous
                or previous.payload["state"] != "shipped"
            ):
                raise HTTPException(409, "Dispatch must be recorded before delivery")
            if command.tracking_number or command.tracking_url:
                raise HTTPException(422, "Delivery retains the recorded dispatch tracking")
            order.delivered_at = datetime.now(timezone.utc)
        order.status = command.state
        version = previous.version + 1 if previous else 1
        payload = {
            "event_id": str(command.event_id),
            "order_id": command.order_id,
            "batchivo_order_id": str(order.id),
            "payment_id": order.payment_id,
            "version": version,
            "state": command.state,
            "tracking_number": order.tracking_number or "",
            "tracking_url": order.tracking_url or "",
            "shipped_at": order.shipped_at.isoformat(),
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        }
        db.add(
            CommerceFulfilmentEvent(
                event_id=str(command.event_id),
                command_sha256=digest,
                woo_order_id=command.order_id,
                version=version,
                payload=payload,
            )
        )
    return {"status": "recorded", "event_id": str(command.event_id), "version": version}


class NativeDispatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: int = Field(gt=0)
    state: Literal["shipped", "delivered"]
    tracking_number: str = Field(default="", max_length=100)
    tracking_url: str = Field(default="", max_length=500)


@app.post("/fulfilment/operator")
async def operator_dispatch(request: Request):
    body = await signed_body(request)
    try:
        command = NativeDispatchRequest.model_validate_json(body)
    except ValueError:
        return signed_response({"ok": False, "code": 422, "error": "Invalid dispatch details"})
    from app.api.v1.orders import ship_order, deliver_order, ShipOrderRequest

    try:
        if command.state == "delivered" and (command.tracking_number or command.tracking_url):
            raise HTTPException(422, "Delivery retains recorded dispatch tracking")
        async with async_session_maker() as db:
            mapping = await db.scalar(
                select(CommerceOrder).where(CommerceOrder.woo_order_id == command.order_id)
            )
            if not mapping:
                raise HTTPException(404, "Mapped paid order not found")
            tenant = await db.get(Tenant, TENANT)
            if command.state == "shipped":
                result = await ship_order(
                    UUID(mapping.batchivo_order_id),
                    ShipOrderRequest(
                        tracking_number=command.tracking_number, tracking_url=command.tracking_url
                    ),
                    db=db,
                    tenant=tenant,
                )
            else:
                result = await deliver_order(UUID(mapping.batchivo_order_id), db=db, tenant=tenant)
            if not result.get("commerce"):
                raise HTTPException(409, "Native commerce dispatch result missing")
            return signed_response(
                {
                    "ok": True,
                    "order_id": command.order_id,
                    "state": command.state,
                    "result": result["commerce"],
                }
            )
    except HTTPException as error:
        return signed_response({"ok": False, "code": error.status_code, "error": str(error.detail)})


@app.post("/fulfilment/pending")
async def pending_fulfilment(request: Request):
    await signed_body(request)
    async with async_session_maker() as db, db.begin():
        events = (
            await db.scalars(
                select(CommerceFulfilmentEvent)
                .where(CommerceFulfilmentEvent.state == "pending")
                .order_by(
                    CommerceFulfilmentEvent.updated_at,
                    CommerceFulfilmentEvent.woo_order_id,
                    CommerceFulfilmentEvent.version,
                )
                .limit(100)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for event in events:
            event.updated_at = datetime.now(timezone.utc)
        return signed_response({"events": [event.payload for event in events]})


@app.post("/fulfilment/ack")
async def acknowledge_fulfilment(request: Request):
    body = await signed_body(request)
    try:
        value = json.loads(body)
        event_id = str(UUID(value["event_id"]))
        order_id = int(value["order_id"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(422, "Invalid acknowledgement")
    async with async_session_maker() as db, db.begin():
        event = await db.scalar(
            select(CommerceFulfilmentEvent)
            .where(
                CommerceFulfilmentEvent.event_id == event_id,
                CommerceFulfilmentEvent.woo_order_id == order_id,
            )
            .with_for_update()
        )
        if not event:
            raise HTTPException(404, "Dispatch event not found")
        event.state = "delivered"
    return signed_response({"status": "acknowledged", "event_id": event_id})


@app.get("/health")
async def health():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "environment": RUNTIME.mode}


async def verify_payment(event: Event):
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            RUNTIME.square_base + "/payments/" + event.payment_id,
            headers={
                "Authorization": "Bearer " + os.environ[RUNTIME.token_environment_key],
                "Square-Version": "2026-01-22",
            },
        )
    if r.status_code != 200:
        raise HTTPException(503, "Square payment verification unavailable")
    p = r.json()["payment"]
    expected_location = os.environ.get(RUNTIME.location_environment_key)
    if not expected_location or p.get("location_id") != expected_location:
        raise HTTPException(409, "Payment location does not match this store")
    if p.get("reference_id") != str(event.order_id):
        raise HTTPException(409, "Payment reference does not match this order")
    if event.reservation_id and not p.get("note", "").startswith(
        "[MF-RESERVATION:" + str(event.reservation_id) + "] "
    ):
        raise HTTPException(409, "Payment does not match the stock reservation")
    if p["status"] != "COMPLETED" or p["amount_money"] != {
        "amount": event.total_pence,
        "currency": "GBP",
    }:
        raise HTTPException(409, "Payment status or amount does not match order")
    target = (
        event.refunded_pence
        if event.refunded_pence is not None
        else (event.total_pence if event.state == "refunded" else 0)
    )
    verified = []
    if target:
        ids = event.refund_ids if event.refunded_pence is not None else p.get("refund_ids", [])
        if not ids or not set(ids).issubset(set(p.get("refund_ids", []))):
            raise HTTPException(
                503, "Expected refund identities are not yet present on Square payment"
            )
        async with httpx.AsyncClient(timeout=20) as client:
            for refund_id in ids:
                refund = await client.get(
                    RUNTIME.square_base + "/refunds/" + refund_id,
                    headers={
                        "Authorization": "Bearer " + os.environ[RUNTIME.token_environment_key],
                        "Square-Version": "2026-01-22",
                    },
                )
                if refund.status_code != 200:
                    raise HTTPException(503, "Refund verification unavailable")
                value = refund.json()["refund"]
                if (
                    value.get("payment_id") != event.payment_id
                    or value.get("amount_money", {}).get("currency") != "GBP"
                ):
                    raise HTTPException(409, "Refund payment identity or currency mismatch")
                if value["status"] != "COMPLETED":
                    raise HTTPException(503, "Refund completion is not yet verified by Square")
                verified.append(
                    {
                        "id": refund_id,
                        "amount_pence": value["amount_money"]["amount"],
                        "status": "COMPLETED",
                    }
                )
        if sum(v["amount_pence"] for v in verified) != target:
            raise HTTPException(409, "Verified refund amount does not match snapshot")
    elif event.refund_ids:
        raise HTTPException(422, "Refund identities require a positive refund amount")
    p["_verified_refunds"] = verified
    p["_verified_refunded_pence"] = target
    return p


@app.post("/events")
async def receive(request: Request):
    body = await signed_body(request)
    try:
        event = Event.model_validate_json(body)
    except ValueError:
        raise HTTPException(422, "Invalid order snapshot")
    digest = hashlib.sha256(body).hexdigest()
    async with async_session_maker() as db, db.begin():
        # Payment lock prevents one captured payment being assigned to two orders.
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,1))"),
            {"key": event.payment_id},
        )
        reused = await db.scalar(
            select(CommerceOrder).where(
                CommerceOrder.snapshot["payment_id"].astext == event.payment_id,
                CommerceOrder.woo_order_id != event.order_id,
            )
        )
        if reused:
            raise HTTPException(409, "Payment already belongs to another order")
        # Transaction-scoped lock serializes duplicate/new events for one order.
        await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": event.order_id})
        prior = await db.scalar(
            select(CommerceReceipt).where(CommerceReceipt.event_id == str(event.event_id))
        )
        if prior:
            if prior.body_sha256 != digest:
                raise HTTPException(409, "Event ID reused with different data")
            recorded = await db.scalar(
                select(CommerceOrder).where(CommerceOrder.woo_order_id == event.order_id)
            )
            return {
                "status": "duplicate",
                "event_id": str(event.event_id),
                "refund_review": recorded.effects.get("refund_review", "") if recorded else "",
                "refunded_pence": recorded.effects.get("refunded_pence", 0) if recorded else 0,
            }
        mapping = await db.scalar(
            select(CommerceOrder)
            .where(CommerceOrder.woo_order_id == event.order_id)
            .with_for_update()
        )
        if mapping and event.version <= mapping.version:
            db.add(
                CommerceReceipt(
                    event_id=str(event.event_id),
                    body_sha256=digest,
                    woo_order_id=event.order_id,
                    outcome="stale",
                )
            )
            return {"status": "stale", "event_id": str(event.event_id)}
        if (
            mapping
            and mapping.state in ["cancelled", "refunded"]
            and event.state in ["processing", "completed"]
        ):
            raise HTTPException(409, "Cannot reopen terminal order through delayed payment event")
        if mapping:
            # Paid quantities and money cannot be rewritten by a later status event.
            old = mapping.snapshot
            new = event.model_dump(mode="json")
            keys = [
                "payment_id",
                "currency",
                "subtotal_pence",
                "shipping_pence",
                "discount_pence",
                "total_pence",
            ]
            line_keys = ["line_id", "product_id", "variant_id", "sku", "quantity", "total_pence"]

            def identity(lines):
                return sorted([tuple(str(line.get(k)) for k in line_keys) for line in lines])

            if (
                any(old[k] != new[k] for k in keys)
                or old.get("reservation_id") != new.get("reservation_id")
                or identity(old["lines"]) != identity(new["lines"])
            ):
                raise HTTPException(
                    409, "Paid order changes require an explicit adjustment workflow"
                )
        payment = await verify_payment(event)
        if mapping and payment["_verified_refunded_pence"] < mapping.effects.get(
            "refunded_pence", 0
        ):
            raise HTTPException(409, "Verified refunds cannot be removed by a later event")
        if mapping and not {r["id"] for r in mapping.effects.get("refunds", [])}.issubset(
            {r["id"] for r in payment["_verified_refunds"]}
        ):
            raise HTTPException(
                409, "Verified refund identities cannot be removed by a later event"
            )
        reservation = None
        if not mapping and event.reservation_id:
            reservation = await db.scalar(
                select(CommerceReservation)
                .where(
                    CommerceReservation.reservation_id == str(event.reservation_id),
                    CommerceReservation.woo_order_id == event.order_id,
                )
                .with_for_update()
            )
            if (
                not reservation
                or reservation.state != "payment_pending"
                or reservation_identity(reservation.snapshot)
                != reservation_identity(event.model_dump(mode="json"))
            ):
                raise HTTPException(409, "Matching payment-pending reservation required")
        if not mapping:
            if event.state not in ["processing", "completed"]:
                raise HTTPException(409, "Paid order must be reconciled before its terminal event")
            order = Order(
                tenant_id=TENANT,
                sales_channel_id=await commerce_sales_channel(
                    db, TENANT, os.environ, RUNTIME.isolated
                ),
                order_number=RUNTIME.order_reference(event.order_id),
                status="processing",
                customer_email=event.customer.get("email", "test@example.invalid"),
                customer_name=event.customer.get("name", "Test customer"),
                customer_phone=event.customer.get("phone") or None,
                shipping_address_line1=event.shipping.get("address_1", ""),
                shipping_address_line2=event.shipping.get("address_2", ""),
                shipping_city=event.shipping.get("city", ""),
                shipping_postcode=event.shipping.get("postcode", ""),
                shipping_country="United Kingdom",
                shipping_method=event.shipping.get("method", "Royal Mail"),
                shipping_cost=Decimal(event.shipping_pence) / 100,
                subtotal=Decimal(event.subtotal_pence) / 100,
                total=Decimal(event.total_pence) / 100,
                discount_amount=Decimal(event.discount_pence) / 100,
                currency="GBP",
                payment_provider="square-sandbox" if RUNTIME.isolated else "square",
                payment_id=event.payment_id,
                payment_status="COMPLETED",
                confirmation_email_sent=False,
                internal_notes=(
                    "Isolated WooCommerce acceptance order. Never dispatch to a real customer."
                    if RUNTIME.isolated
                    else "WooCommerce owns payment, refund and customer email actions; dispatch through the commerce workflow."
                ),
            )
            db.add(order)
            await db.flush()
            effects = {"stock": [], "restored": False, "jobs": []}
            for line in sorted(event.lines, key=lambda x: str(x.product_id)):
                product = await db.scalar(
                    select(Product)
                    .where(Product.id == line.product_id, Product.tenant_id == TENANT)
                    .with_for_update()
                )
                if not product or not product.is_active:
                    raise HTTPException(409, "Unknown or inactive mapped product")
                variant = None
                if line.variant_id:
                    variant = await db.scalar(
                        select(ProductVariant)
                        .where(
                            ProductVariant.id == line.variant_id,
                            ProductVariant.product_id == product.id,
                            ProductVariant.tenant_id == TENANT,
                            ProductVariant.is_active.is_(True),
                        )
                        .with_for_update()
                    )
                    if not variant:
                        raise HTTPException(409, "Invalid mapped variant")
                if line.sku != (variant.sku if variant else product.sku):
                    raise HTTPException(409, "SKU does not match source mapping")
                pto = (
                    variant.fulfilment_type in ["print_to_order", "made_to_order"]
                    if variant
                    else product.print_to_order
                )
                if not pto:
                    if not reservation:
                        raise HTTPException(409, "Finite stock requires a pre-payment reservation")
                    stock = variant or product
                    if stock.units_in_stock < line.quantity:
                        raise HTTPException(409, "Insufficient Batchivo stock")
                    stock.units_in_stock -= line.quantity
                    effects["stock"].append(
                        {
                            "product_id": str(product.id),
                            "variant_id": str(variant.id) if variant else None,
                            "quantity": line.quantity,
                        }
                    )
                db.add(
                    OrderItem(
                        tenant_id=TENANT,
                        order_id=order.id,
                        product_id=product.id,
                        product_sku=line.sku,
                        product_name=(line.name + " " + line.option).strip()[:255],
                        quantity=line.quantity,
                        unit_price=Decimal(line.total_pence) / 100 / line.quantity,
                        total_price=Decimal(line.total_pence) / 100,
                    )
                )
                if pto:
                    job = PrintJob(
                        id=uuid4(),
                        tenant_id=TENANT,
                        product_id=product.id,
                        quantity=line.quantity,
                        status=JobStatus.PENDING,
                        reference=RUNTIME.job_reference(event.order_id, line.line_id),
                        notes=json.dumps(
                            {
                                "source": RUNTIME.source,
                                "variant_id": str(line.variant_id) if line.variant_id else None,
                                "sku": line.sku,
                                "option": line.option,
                                "payment_id": event.payment_id,
                            }
                        ),
                    )
                    db.add(job)
                    effects.setdefault("jobs", []).append(
                        {"id": str(job.id), "line_id": line.line_id}
                    )
            if reservation:
                reservation.state = "committed"
            mapping = CommerceOrder(
                woo_order_id=event.order_id,
                batchivo_order_id=str(order.id),
                version=event.version,
                state=event.state,
                snapshot=event.model_dump(mode="json"),
                effects=effects,
            )
            db.add(mapping)
        else:
            order = await db.get(Order, UUID(mapping.batchivo_order_id))
            mapping.version = event.version
            mapping.state = event.state
            mapping.snapshot = event.model_dump(mode="json")
            effects = dict(mapping.effects)
            if payment["_verified_refunded_pence"]:
                effects["refunds"] = payment["_verified_refunds"]
                effects["refunded_pence"] = payment["_verified_refunded_pence"]
                order.payment_status = (
                    "REFUNDED"
                    if payment["_verified_refunded_pence"] == event.total_pence
                    else "PARTIALLY_REFUNDED"
                )
                if order.payment_status == "PARTIALLY_REFUNDED":
                    from app.commerce_disposition import refund_release_valid

                    if not refund_release_valid(effects, payment):
                        effects["refund_review"] = (
                            "Partial refund requires a fresh fulfilment decision before new manufacturing or dispatch."
                        )
            if event.state in ["cancelled", "refunded"]:
                jobs = (
                    await db.scalars(
                        select(PrintJob)
                        .where(
                            PrintJob.tenant_id == TENANT,
                            PrintJob.reference.like(RUNTIME.order_reference(event.order_id) + ":%"),
                        )
                        .with_for_update()
                    )
                ).all()
                started = any(
                    j.status not in [JobStatus.PENDING, JobStatus.QUEUED, JobStatus.CANCELLED]
                    for j in jobs
                )
                dispatched = bool(order.shipped_at)
                if event.state == "cancelled" and (started or dispatched):
                    raise HTTPException(
                        409,
                        "Manufacturing/dispatch already started; cancellation requires operator review",
                    )
                # Refund is a financial fact. Never erase completed/active manufacturing or dispatch.
                if event.state == "refunded" and (started or dispatched):
                    effects["refund_review"] = (
                        "Refund after manufacturing or dispatch: review goods/returns; no stock restored."
                    )
                    for job in jobs:
                        if job.status in [JobStatus.PENDING, JobStatus.QUEUED]:
                            job.status = JobStatus.CANCELLED
                else:
                    for job in jobs:
                        job.status = JobStatus.CANCELLED
                    if not effects.get("restored"):
                        for effect in effects.get("stock", []):
                            cls = ProductVariant if effect["variant_id"] else Product
                            key = UUID(effect["variant_id"] or effect["product_id"])
                            stock = await db.scalar(
                                select(cls)
                                .where(cls.id == key, cls.tenant_id == TENANT)
                                .with_for_update()
                            )
                            if not stock:
                                raise HTTPException(409, "Stock mapping requires operator review")
                            stock.units_in_stock += effect["quantity"]
                        effects["restored"] = True
                if not dispatched:
                    order.status = event.state
                if event.state == "refunded":
                    order.payment_status = "REFUNDED"
            mapping.effects = effects
        await db.flush()
        await enrich_job_options(db, event)
        db.add(
            CommerceReceipt(
                event_id=str(event.event_id),
                body_sha256=digest,
                woo_order_id=event.order_id,
                outcome="applied",
            )
        )
    return {
        "status": "applied",
        "event_id": str(event.event_id),
        "batchivo_order_id": mapping.batchivo_order_id,
        "refund_review": mapping.effects.get("refund_review", ""),
        "refunded_pence": mapping.effects.get("refunded_pence", 0),
    }


async def seed(file):
    if not RUNTIME.isolated:
        raise RuntimeError("Catalogue seeding is prohibited in production")
    d = json.load(open(file))
    if d["_export"]["tenant_id"] != str(TENANT):
        raise RuntimeError("Wrong source tenant")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(lambda sync: payment_identity_index.create(sync, checkfirst=True))
    async with async_session_maker() as db, db.begin():
        if not await db.get(Tenant, TENANT):
            db.add(
                Tenant(
                    id=TENANT,
                    name="Mystmere Forge — isolated commerce test",
                    slug="mystmere-commerce-test",
                    settings={},
                )
            )
        await db.flush()
        for table in ["designers", "categories", "products", "product_variants"]:
            rows = d[table]
            for row in rows:
                row = dict(row)
                if table == "designers":
                    row["notes"] = None
                if table == "products":
                    row["packaging_consumable_id"] = None
                cols = [
                    c.name
                    for c in Base.metadata.tables[table].columns
                    if c.name in row and not c.computed
                ]
                names = ",".join('"' + c + '"' for c in cols)
                # Only insert missing records; reseeding never resets stock or test orders.
                await db.execute(
                    text(
                        f"INSERT INTO {table} ({names}) SELECT {names} FROM json_populate_record(NULL::{table},CAST(:row AS json)) ON CONFLICT(id) DO NOTHING"
                    ),
                    {"row": json.dumps(row)},
                )
    print(
        "Isolated Batchivo schema and catalogue seeded; no production customers, credentials or printers copied."
    )


async def reconcile_job_options():
    if not RUNTIME.isolated:
        raise RuntimeError("Fixture enrichment is prohibited in production")
    async with async_session_maker() as db, db.begin():
        mappings = (await db.scalars(select(CommerceOrder).with_for_update())).all()
        changed = 0
        for mapping in mappings:
            changed += await enrich_job_options(db, Event.model_validate(mapping.snapshot))
    print(
        json.dumps(
            {
                "option_labels_enriched": changed,
                "scope": "Isolated variant labels only; quantities, status, payments and stock unchanged",
            }
        )
    )


if __name__ != "__main__":
    from app.commerce_returns import install_routes as install_return_routes

    install_return_routes(app)
    from app.commerce_disposition import install_routes as install_disposition_routes

    install_disposition_routes(app)

if __name__ == "__main__":
    asyncio.run(
        reconcile_job_options() if sys.argv[1] == "--reconcile-job-options" else seed(sys.argv[1])
    )
