"""ProductComponent model - join table linking Products to other Products (bundles/sets)."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.product import Product


class ProductComponent(Base, UUIDMixin, TimestampMixin):
    """
    Join table linking Products to other Products (parent-child) with quantity.

    Enables composite products (bundles, sets, kits) where a Product can contain
    other Products. For example:
    - "Finger Dino Set - Steggy" contains "Finger Dino Egg" + individual models
    - "Mega Bundle" contains multiple individual products

    This is separate from ProductModel which links Products to Models (printed items).
    A Product can have both:
    - ProductModels: individual printed items (Models)
    - ProductComponents: other sellable Products (bundles within bundles)

    Cost calculation traverses this relationship recursively with cycle detection.
    """

    __tablename__ = "product_components"

    # Parent product (the bundle/set that contains other products)
    parent_product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent product (the bundle/set)",
    )

    # Child product (the product contained within the parent)
    child_product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Child product included in the parent",
    )

    # Quantity of child product in the parent
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Number of this child product in the parent (e.g., 2 eggs in a set)",
    )

    # Relationships
    parent_product: Mapped["Product"] = relationship(
        "Product",
        foreign_keys=[parent_product_id],
        back_populates="child_products",
    )

    child_product: Mapped["Product"] = relationship(
        "Product",
        foreign_keys=[child_product_id],
        back_populates="parent_products",
        lazy="joined",  # Eager load for cost calculation
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_product_component_quantity_positive"),
        CheckConstraint(
            "parent_product_id != child_product_id",
            name="check_no_self_reference",
        ),
        UniqueConstraint(
            "parent_product_id",
            "child_product_id",
            name="uq_product_component_parent_child",
        ),
        {"comment": "Links parent products to child products (bundles/sets)"},
    )

    def __repr__(self) -> str:
        return f"<ProductComponent(parent={self.parent_product_id}, child={self.child_product_id}, qty={self.quantity})>"
