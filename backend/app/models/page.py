"""Page model for content management (policy pages, etc.)."""

import uuid
from enum import Enum as PyEnum

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class PageType(str, PyEnum):
    """Types of content pages."""

    POLICY = "policy"  # Privacy, Terms, Returns, etc.
    INFO = "info"  # Shipping info, FAQ, About
    LEGAL = "legal"  # Legal notices


class Page(Base, UUIDMixin, TimestampMixin):
    """
    Content page for shop policies and information.

    Used for storing editable content like:
    - Privacy Policy
    - Terms & Conditions
    - Returns Policy
    - Shipping Information
    - About Us
    """

    __tablename__ = "pages"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Page identification
    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="URL-friendly identifier (e.g., 'privacy-policy')",
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Page title displayed to users",
    )

    # Content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="Page content in Markdown format",
    )

    # Metadata
    page_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PageType.POLICY.value,
        comment="Page type: policy, info, legal",
    )

    meta_description: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="SEO meta description",
    )

    # Status
    is_published: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether page is publicly visible",
    )

    # Display order for listing pages
    sort_order: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="Sort order for page listings",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_page_tenant_slug"),
        {"comment": "Content pages for policies and information"},
    )

    def __repr__(self) -> str:
        return f"<Page(slug={self.slug}, title={self.title})>"
