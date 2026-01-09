"""TenantModule model for per-tenant module access control."""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class TenantModule(Base, UUIDMixin, TimestampMixin):
    """
    TenantModule controls which modules are enabled/disabled per tenant.

    This allows platform admins to customize module access for each tenant,
    enabling features like different module sets for different business types
    (3D printing vs hand knitting vs machine knitting).
    """

    __tablename__ = "tenant_modules"

    # Tenant reference
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant this module configuration belongs to",
    )

    # Module identification
    module_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Module identifier (e.g., 'spools', 'models', 'printers')",
    )

    # Enabled status
    enabled: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,
        comment="Whether this module is enabled for the tenant",
    )

    # Audit trail - who made the change
    enabled_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who last changed the enabled status (null if system-set)",
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship(
        "Tenant",
        back_populates="modules",
        lazy="select",
    )

    enabled_by: Mapped[Optional["User"]] = relationship(
        "User",
        lazy="select",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "module_name", name="uq_tenant_modules_tenant_module"),
        {"comment": "Module enable/disable configuration per tenant"},
    )

    def __repr__(self) -> str:
        return f"<TenantModule(tenant_id={self.tenant_id}, module={self.module_name}, enabled={self.enabled})>"
