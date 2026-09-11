"""Reviewed, explicit grants for a dedicated single-store commerce database role.

Generates SQL only. An operator-controlled migration connection applies it in a
transaction after provisioning a fresh role and the commerce schema. Passwords
never belong in this module. Native application credentials remain separate.
"""

import re
from uuid import UUID

TENANT_TABLES = {
    "tenants": "id",
    "products": "tenant_id",
    "product_variants": "tenant_id",
    "orders": "tenant_id",
    "order_items": "tenant_id",
    "print_jobs": "tenant_id",
    "sales_channels": "tenant_id",
}
LEDGERS = (
    "commerce_orders",
    "commerce_receipts",
    "commerce_reservations",
    "commerce_fulfilment_events",
)


def policy_sql(role: str, tenant_id: UUID) -> list[str]:
    if not re.fullmatch(r"mf_commerce_[a-z0-9_]{1,32}", role):
        raise ValueError("Dedicated commerce role name required")
    tenant = str(UUID(str(tenant_id)))
    role_sql = '"' + role + '"'
    statements = [f"GRANT USAGE ON SCHEMA public TO {role_sql}"]
    context = f"NULLIF(current_setting('app.current_tenant_id', true), '')::uuid = '{tenant}'::uuid"
    for table in (*TENANT_TABLES, *LEDGERS):
        predicate = context
        if table in TENANT_TABLES:
            predicate += f" AND {TENANT_TABLES[table]} = '{tenant}'::uuid"
        statements.extend(
            [
                f"REVOKE ALL ON TABLE public.{table} FROM {role_sql}",
                f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY",
                f"DROP POLICY IF EXISTS {role}_allow ON public.{table}",
                f"DROP POLICY IF EXISTS {role}_fence ON public.{table}",
                # A restrictive policy keeps older permissive tenant policies from
                # letting this role choose a different tenant through set_config().
                f"CREATE POLICY {role}_allow ON public.{table} AS PERMISSIVE FOR ALL TO {role_sql} USING (true) WITH CHECK (true)",
                f"CREATE POLICY {role}_fence ON public.{table} AS RESTRICTIVE FOR ALL TO {role_sql} USING ({predicate}) WITH CHECK ({predicate})",
                f"GRANT SELECT ON TABLE public.{table} TO {role_sql}",
            ]
        )
    for table in ("products", "product_variants"):
        statements.append(
            f"GRANT UPDATE (units_in_stock, updated_at) ON public.{table} TO {role_sql}"
        )
    for table in ("orders", "print_jobs", *LEDGERS):
        statements.append(f"GRANT INSERT, UPDATE ON public.{table} TO {role_sql}")
    statements.append(f"GRANT INSERT ON public.order_items TO {role_sql}")
    return statements
