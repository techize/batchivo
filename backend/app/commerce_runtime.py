"""Explicit commerce identities; production activation is a separate release action.

No secrets are retained in this object or included in configuration errors.
"""

from dataclasses import dataclass
import re
from typing import Mapping
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class CommerceRuntime:
    mode: str
    square_base: str
    token_environment_key: str
    location_environment_key: str
    order_prefix: str
    source: str

    @property
    def isolated(self):
        return self.mode == "isolated-test"

    @classmethod
    def from_environment(cls, env: Mapping[str, str]):
        mode = env.get("COMMERCE_MODE", "isolated-test")
        try:
            target = env.get("DATABASE_URL", "")
            if env.get("RLS_ENABLED", "false").lower() in {"true", "1", "yes", "on"} and env.get(
                "RLS_DATABASE_URL"
            ):
                target = env["RLS_DATABASE_URL"]
            database = urlsplit(target)
            name = unquote(database.path.removeprefix("/"))
            host = database.hostname
        except ValueError:
            raise RuntimeError("Invalid commerce database configuration") from None
        if (
            database.scheme not in {"postgresql+psycopg", "postgresql+asyncpg", "postgresql"}
            or not host
        ):
            raise RuntimeError("Commerce requires an explicit PostgreSQL target")
        if mode == "isolated-test":
            if env.get("COMMERCE_ISOLATED") != "true" or name != "batchivo_commerce_test":
                raise RuntimeError("Commerce acceptance bridge requires an isolated test database")
            return cls(
                mode,
                "https://connect.squareupsandbox.com/v2",
                "SQUARE_SANDBOX_ACCESS_TOKEN",
                "SQUARE_SANDBOX_LOCATION_ID",
                "WOO-TEST-",
                "woocommerce-test",
            )
        if mode != "production":
            raise RuntimeError("Unknown commerce runtime mode")
        if (
            env.get("COMMERCE_ISOLATED") != "false"
            or env.get("COMMERCE_PRODUCTION_ENABLED") != "true"
        ):
            raise RuntimeError("Production commerce release is not activated")
        if not re.fullmatch(r"[a-f0-9]{40}|[a-f0-9]{64}", env.get("COMMERCE_RELEASE_ID", "")):
            raise RuntimeError("Production commerce requires a versioned release identity")
        if name != "batchivo" or host not in {
            "postgres.batchivo.svc",
            "postgres.batchivo.svc.cluster.local",
        }:
            raise RuntimeError(
                "Production commerce database identity does not match the reviewed target"
            )
        if not env.get("SQUARE_PRODUCTION_ACCESS_TOKEN") or not env.get(
            "SQUARE_PRODUCTION_LOCATION_ID"
        ):
            raise RuntimeError("Production commerce payment configuration is incomplete")
        return cls(
            mode,
            "https://connect.squareup.com/v2",
            "SQUARE_PRODUCTION_ACCESS_TOKEN",
            "SQUARE_PRODUCTION_LOCATION_ID",
            "WOO-",
            "woocommerce",
        )

    def order_reference(self, order_id):
        return f"{self.order_prefix}{int(order_id)}"

    def job_reference(self, order_id, line_id):
        return f"{self.order_reference(order_id)}:{int(line_id)}"
