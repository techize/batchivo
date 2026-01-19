"""Tenant model for multi-tenancy support."""

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.print_job import PrintJob
    from app.models.printer import Printer
    from app.models.tenant_module import TenantModule
    from app.models.user import UserTenant


class TenantType(str, Enum):
    """
    Tenant type defining the craft/business category.

    Each type enables different modules, features, and terminology:
    - THREE_D_PRINT: 3D printing businesses (filament, printers, models)
    - HAND_KNITTING: Hand knitting crafters (yarn, needles, patterns)
    - MACHINE_KNITTING: Machine knitting (yarn, machines, gauges)
    - GENERIC: General maker/crafter (flexible configuration)
    """

    THREE_D_PRINT = "three_d_print"
    HAND_KNITTING = "hand_knitting"
    MACHINE_KNITTING = "machine_knitting"
    GENERIC = "generic"


class Tenant(Base, UUIDMixin, TimestampMixin):
    """
    Tenant model representing an organization/business using the platform.

    Each tenant has complete data isolation via PostgreSQL Row-Level Security.
    Multiple users can belong to a tenant with different roles.
    """

    __tablename__ = "tenants"

    # Basic Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Tenant/Organization name",
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-safe identifier for tenant",
    )

    # Tenant Type (determines features, modules, terminology)
    tenant_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=TenantType.THREE_D_PRINT.value,
        index=True,
        comment="Tenant business type (three_d_print, hand_knitting, machine_knitting, generic)",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether tenant is active (for soft deletion)",
    )

    # Configuration
    settings: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        comment="Tenant-specific settings (branding, preferences, etc.)",
    )

    # Optional fields
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description of the tenant/business",
    )

    # Currency settings
    currency_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="GBP",
        comment="ISO 4217 currency code (e.g., GBP, USD, EUR)",
    )

    currency_symbol: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        default="£",
        comment="Currency symbol for display (e.g., £, $, €)",
    )

    # Relationships
    user_tenants: Mapped[list["UserTenant"]] = relationship(
        "UserTenant",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    production_runs: Mapped[list["ProductionRun"]] = relationship(
        "ProductionRun",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    printers: Mapped[list["Printer"]] = relationship(
        "Printer",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    print_jobs: Mapped[list["PrintJob"]] = relationship(
        "PrintJob",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )

    # Module access control
    modules: Mapped[list["TenantModule"]] = relationship(
        "TenantModule",
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name='{self.name}', slug='{self.slug}')>"
