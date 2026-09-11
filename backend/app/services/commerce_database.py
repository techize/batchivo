"""Separate commerce connection ownership from the native application engine."""

import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.commerce_runtime import CommerceRuntime
from app.services.commerce_database_policy import LEDGERS, TENANT_TABLES


def commerce_engine(runtime, environment, native_engine):
    target = environment.get("COMMERCE_DATABASE_URL")
    if not runtime.isolated and not target:
        raise RuntimeError("Production commerce requires its dedicated database credential")
    if not target:
        return native_engine
    CommerceRuntime.from_environment(
        {**environment, "DATABASE_URL": target, "RLS_ENABLED": "false"}
    )
    return create_async_engine(target, echo=False, pool_pre_ping=True, pool_size=5, max_overflow=5)


def verify_commerce_role(connection):
    role = (
        connection.execute(
            text(
                "SELECT current_user AS name, rolsuper, rolbypassrls, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname=current_user"
            )
        )
        .mappings()
        .one()
    )
    if not re.fullmatch(r"mf_commerce_[a-z0-9_]{1,32}", role["name"]) or any(
        role[k] for k in ("rolsuper", "rolbypassrls", "rolcreatedb", "rolcreaterole")
    ):
        raise RuntimeError("Commerce database role has unsafe privileges")
    if connection.scalar(
        text(
            "SELECT count(*) FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user)"
        )
    ):
        raise RuntimeError("Commerce database role cannot inherit or assume another role")
    names = list(TENANT_TABLES) + list(LEDGERS)
    rows = (
        connection.execute(
            text(
                "SELECT relname, relrowsecurity, pg_get_userbyid(relowner)=current_user AS owned FROM pg_class WHERE relnamespace='public'::regnamespace AND relname = ANY(:names)"
            ),
            {"names": names},
        )
        .mappings()
        .all()
    )
    if len(rows) != len(names) or any(row["owned"] or not row["relrowsecurity"] for row in rows):
        raise RuntimeError("Commerce schema ownership or row security is not ready")
    if connection.scalar(text("SELECT has_schema_privilege(current_user,'public','CREATE')")):
        raise RuntimeError("Commerce role cannot own schema creation")
