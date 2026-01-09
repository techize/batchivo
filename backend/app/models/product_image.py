"""Product image model for shop display."""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.product import Product


class ProductImage(Base, UUIDMixin, TimestampMixin):
    """
    Product image for shop display.

    Supports multiple images per product with ordering and primary image designation.
    Images are stored in MinIO/local filesystem with URLs stored in this table.
    """

    __tablename__ = "product_images"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Product reference
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Product this image belongs to",
    )

    # Image details
    image_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Storage path/URL to the image file",
    )

    thumbnail_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Storage path/URL to the thumbnail version",
    )

    alt_text: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        server_default="",
        comment="Alt text for accessibility",
    )

    # Ordering and status
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Sort order for display (lower = first)",
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Whether this is the primary product image",
    )

    # Original filename for reference
    original_filename: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Original uploaded filename",
    )

    # File metadata
    file_size: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="File size in bytes",
    )

    content_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="MIME type of the image",
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="images",
        lazy="selectin",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("product_id", "display_order", name="uq_product_image_order"),
        {"comment": "Product images for shop display"},
    )

    def __repr__(self) -> str:
        return f"<ProductImage(product_id={self.product_id}, order={self.display_order}, primary={self.is_primary})>"
