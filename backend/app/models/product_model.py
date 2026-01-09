"""ProductModel model - join table linking Products to Models with quantity."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.model import Model
    from app.models.product import Product


class ProductModel(Base, UUIDMixin, TimestampMixin):
    """
    Join table linking Products to Models with quantity.

    Represents how many of each Model is needed to make a Product.
    Example: Red Squirrel Set contains 5x Hazelnut, 5x Acorn, 1x Squirrel, etc.
    """

    __tablename__ = "product_models"

    # References
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Product this model belongs to",
    )

    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("models.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Model included in this product",
    )

    # Quantity
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Number of this model in the product (e.g., 5 hazelnuts)",
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="product_models",
    )

    model: Mapped["Model"] = relationship(
        "Model",
        back_populates="product_models",
        lazy="joined",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_quantity_positive"),
        {"comment": "Links products to their constituent models with quantities"},
    )

    def __repr__(self) -> str:
        return f"<ProductModel(product_id={self.product_id}, model_id={self.model_id}, qty={self.quantity})>"
