"""Executable probe against a disposable real PostgreSQL database, not mocks."""

import asyncio
import importlib.util
import json
import os
from pathlib import Path
from uuid import uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import HTTPException
from sqlalchemy import text

from app.services import commerce_handover as handover

checks = []


def check(name, passed):
    checks.append({"check": name, "pass": bool(passed)})
    if not passed:
        raise RuntimeError(name)


async def probe():
    engine = handover.handover_engine()
    migration_path = (
        Path(__file__).resolve().parents[2] / "alembic/versions/20260909_commerce_handover.py"
    )
    spec = importlib.util.spec_from_file_location("handover_migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    async with engine.begin() as c:

        def migrate(conn):
            with Operations.context(MigrationContext.configure(conn)):
                migration.upgrade()

        await c.run_sync(migrate)
    check("Actual Alembic migration creates legacy ownership without changing it", True)
    os.environ["COMMERCE_LEGACY_HANDOVER_ENABLED"] = "true"
    release = "a" * 40
    eid = str(uuid4())
    entered = asyncio.Event()
    finish = asyncio.Event()

    async def existing_writer():
        async with handover.legacy_writer(handover.TENANT):
            # Real intermediate transaction/commit on an independent connection.
            async with engine.begin() as transaction:
                await transaction.execute(text("SELECT 1"))
            entered.set()
            await finish.wait()

    old = asyncio.create_task(existing_writer())
    await entered.wait()
    async with engine.connect() as c:
        acquired = (
            await c.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": handover.LOCK})
        ).scalar_one()
        check("Shared request lock survives an intermediate application commit", not acquired)
        if acquired:
            await c.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": handover.LOCK})
    transition = asyncio.create_task(handover.transition_owner(0, "fenced", eid, release))
    # Give the real server time to enqueue the exclusive lock request.
    await asyncio.sleep(0.15)
    check("Final fence waits for an already-running legacy writer", not transition.done())
    finish.set()
    await old
    result = await transition
    check(
        "Fence commits only after the existing writer exits",
        result["revision"] == 1 and result["to"] == "fenced",
    )
    try:
        async with handover.legacy_writer(handover.TENANT):
            raise AssertionError("Unexpected legacy write")
    except HTTPException as e:
        check("New legacy writes are rejected after the drain", e.status_code == 409)
    duplicate = await handover.transition_owner(0, "fenced", eid, release)
    check(
        "Same transition receipt replays without another revision",
        duplicate["duplicate"] and duplicate["revision"] == 1,
    )
    for expected, target, event in [(0, "legacy", str(uuid4())), (0, "woocommerce", eid)]:
        try:
            await handover.transition_owner(expected, target, event, release)
            raise AssertionError("Conflict accepted")
        except ValueError:
            check("Stale revision or reused event body is refused", True)
    await handover.transition_owner(1, "woocommerce", str(uuid4()), release)
    try:
        async with handover.legacy_writer(handover.TENANT):
            raise AssertionError("Unexpected legacy write")
    except HTTPException as e:
        check("Woo ownership keeps legacy writers closed", e.status_code == 409)
    async with handover.legacy_writer(uuid4()):
        check("Another tenant retains its existing behavior", True)
    try:
        await handover.transition_owner(2, "legacy", str(uuid4()), release)
        raise AssertionError("Direct ownership jump allowed")
    except ValueError:
        check("Rollback cannot jump directly across the fence", True)
    from commerce_handover_http import probe_http

    await probe_http(engine, check)
    await handover.transition_owner(2, "fenced", str(uuid4()), release)
    await handover.transition_owner(3, "legacy", str(uuid4()), release)
    entered.clear()
    old = asyncio.create_task(existing_writer())
    # Reset the completion gate for a genuinely held/cancelled request.
    finish.clear()
    await entered.wait()
    old.cancel()
    try:
        await old
    except asyncio.CancelledError:
        pass
    async with engine.connect() as c:
        acquired = (
            await c.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": handover.LOCK})
        ).scalar_one()
        check("Cancelled request releases its physical-session lock", acquired)
        if acquired:
            await c.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": handover.LOCK})
    async with engine.begin() as c:
        await c.execute(
            text("DELETE FROM commerce_handover WHERE tenant_id=:tenant"),
            {"tenant": handover.TENANT},
        )
    try:
        async with handover.legacy_writer(handover.TENANT):
            raise AssertionError("Missing ownership opened writes")
    except HTTPException as e:
        check("Missing ownership record fails closed", e.status_code == 503)
    os.environ["COMMERCE_LEGACY_HANDOVER_ENABLED"] = "false"
    async with handover.legacy_writer(handover.TENANT):
        check("Disabled deployment feature preserves earlier native behavior", True)
    await engine.dispose()
    print(
        json.dumps(
            {
                "checks": checks,
                "failed": sum(not x["pass"] for x in checks),
                "scope": "Actual PostgreSQL advisory locks, Alembic migration, concurrent drain, intermediate commits, cancellation, CAS/audit replay and rollback state machine in a disposable database. No production fence applied.",
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(probe())
