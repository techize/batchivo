"""Drain legacy writers before final sync; old callbacks and reads remain available.

A session-level shared lock spans the complete request, including intermediate
application commits. A separate bounded pool avoids deadlocks with request DBs.
"""

import os
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.auth.customer_dependencies import CurrentCustomer, decode_customer_token
from app.auth.dependencies import ShopTenant
from app.database import engine as native_engine
from app.database import get_db
from app.schemas.customer import CustomerRefreshToken

TENANT = UUID("ad62b515-17b3-4830-bcb4-3f4c470c26e2")
LOCK = 0x4D4653484F50


@lru_cache(maxsize=1)
def handover_engine():
    return create_async_engine(
        native_engine.url, pool_pre_ping=True, pool_size=2, max_overflow=3, pool_timeout=20
    )


@asynccontextmanager
async def legacy_writer(tenant_id):
    if os.environ.get("COMMERCE_LEGACY_HANDOVER_ENABLED") != "true" or tenant_id != TENANT:
        yield
        return
    async with handover_engine().connect() as connection:
        locked = False
        try:
            await connection.execute(text("SELECT pg_advisory_lock_shared(:key)"), {"key": LOCK})
            locked = True
            owner = (
                await connection.execute(
                    text("SELECT owner FROM commerce_handover WHERE tenant_id=:tenant"),
                    {"tenant": TENANT},
                )
            ).scalar_one_or_none()
            await connection.commit()
            if owner != "legacy":
                message = (
                    "The shop is being upgraded. Please reload www.mystmereforge.co.uk to continue. "
                    "Your account and previous orders are preserved. Check an existing payment before starting another checkout."
                )
                raise HTTPException(
                    409 if owner in ("fenced", "woocommerce") else 503,
                    message,
                    headers={"Retry-After": "5"},
                )
            yield
        finally:
            if locked:
                try:
                    await connection.execute(
                        text("SELECT pg_advisory_unlock_shared(:key)"), {"key": LOCK}
                    )
                    await connection.commit()
                except BaseException:
                    # An interrupted cleanup must discard the physical connection,
                    # never return a session advisory lock to the pool.
                    await connection.invalidate()
                    raise


async def legacy_shop_write_guard(request: Request, tenant: ShopTenant):
    if request.method in ("GET", "HEAD", "OPTIONS"):
        yield
        return
    async with legacy_writer(tenant.id):
        yield


async def legacy_customer_write_guard(request: Request, customer: CurrentCustomer):
    if request.method in ("GET", "HEAD", "OPTIONS"):
        yield
        return
    async with legacy_writer(customer.tenant_id):
        yield


async def legacy_refresh_write_guard(data: CustomerRefreshToken):
    token = decode_customer_token(data.refresh_token)
    # The existing endpoint validates token type/account. No unverified tenant
    # or caller-supplied hostname can bypass the writer's signed token identity.
    async with legacy_writer(token.tenant_id if token else None):
        yield


async def transition_owner(expected_revision: int, target: str, event_id: str, release_id: str):
    """Operator-only CAS transition, draining all legacy requests before a fence.

    No HTTP route exposes this function. The promotion controller must separately
    close Woo checkout and reconcile payments before moving ownership back.
    """
    import json
    import re
    from datetime import UTC, datetime

    if target not in {"legacy", "fenced", "woocommerce"} or expected_revision < 0:
        raise ValueError("Invalid handover state")
    UUID(event_id)
    if not re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", release_id):
        raise ValueError("Versioned release identity required")
    async with handover_engine().connect() as connection:
        locked = False
        try:
            await connection.execute(text("SET lock_timeout='120s'"))
            await connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": LOCK})
            locked = True
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT owner,revision,audit FROM commerce_handover WHERE tenant_id=:tenant FOR UPDATE"
                        ),
                        {"tenant": TENANT},
                    )
                )
                .mappings()
                .one()
            )
            for entry in row["audit"]:
                if entry["event_id"] == event_id:
                    if (
                        entry["to"] != target
                        or entry["release_id"] != release_id
                        or entry["revision"] != expected_revision + 1
                    ):
                        raise ValueError("Handover event identity conflict")
                    return {**entry, "duplicate": True}
            if row["revision"] != expected_revision:
                raise ValueError("Handover revision changed; re-read state")
            if (row["owner"], target) not in {
                ("legacy", "fenced"),
                ("fenced", "legacy"),
                ("fenced", "woocommerce"),
                ("woocommerce", "fenced"),
            }:
                raise ValueError("Ownership must pass through the closed fence")
            entry = {
                "event_id": event_id,
                "from": row["owner"],
                "to": target,
                "revision": expected_revision + 1,
                "release_id": release_id,
                "at": datetime.now(UTC).isoformat(),
            }
            await connection.execute(
                text(
                    "UPDATE commerce_handover SET owner=:owner,revision=:revision,updated_at=now(),audit=audit || CAST(:audit AS jsonb) WHERE tenant_id=:tenant"
                ),
                {
                    "owner": target,
                    "revision": expected_revision + 1,
                    "audit": json.dumps([entry]),
                    "tenant": TENANT,
                },
            )
            await connection.commit()
            return {**entry, "duplicate": False}
        finally:
            if locked:
                try:
                    await connection.rollback()
                    await connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK})
                    await connection.commit()
                except BaseException:
                    await connection.invalidate()
                    raise


async def legacy_product_write_guard(
    request: Request, db: Annotated[AsyncSession, Depends(get_db)]
):
    """Review endpoints resolve ownership from the product, not a new header."""
    if os.environ.get("COMMERCE_LEGACY_HANDOVER_ENABLED") != "true":
        yield
        return
    from sqlalchemy import select

    from app.models.product import Product

    try:
        product = UUID(request.path_params["product_id"])
    except (KeyError, ValueError):
        yield
        return
    tenant = await db.scalar(select(Product.tenant_id).where(Product.id == product))
    async with legacy_writer(tenant):
        yield
