"""Product model for sellable items (composed of one or more Models)."""

import uuid
from typing import TYPE_CHECKING, List, Optional
from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeEngine


class TSVectorType(TypeDecorator):
    """
    A tsvector type that falls back to TEXT for non-PostgreSQL databases.

    This allows the model to work with both PostgreSQL (for FTS) and SQLite (for testing).
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect) -> TypeEngine:
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import TSVECTOR

            return dialect.type_descriptor(TSVECTOR())
        else:
            # Fallback to TEXT for SQLite and other databases
            return dialect.type_descriptor(Text())


from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.consumable import ConsumableType
    from app.models.designer import Designer
    from app.models.print_job import PrintJob
    from app.models.product_component import ProductComponent
    from app.models.product_image import ProductImage
    from app.models.product_model import ProductModel
    from app.models.product_pricing import ProductPricing
    from app.models.production_run import ProductionRun
    from app.models.review import Review


class Product(Base, UUIDMixin, TimestampMixin):
    """
    Product represents a sellable item composed of one or more Models and/or other Products.

    A Product can be:
    - A single Model sold directly (e.g., "Dragon Body")
    - A composite of multiple Models (e.g., "Red Squirrel Set" = 26 models)
    - A bundle of other Products (e.g., "Mega Bundle" = Product A + Product B)
    - Any combination of Models and Products

    Products have their own pricing per sales channel and track packaged
    inventory separately from printed model inventory.

    Composite products (bundles) use ProductComponent to link to child products,
    while ProductModel links to individual printed Models.
    """

    __tablename__ = "products"

    # Tenant isolation
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenant isolation",
    )

    # Designer attribution
    designer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("designers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Designer who created this product's 3D model(s)",
    )

    # Product identification
    sku: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Stock Keeping Unit (unique per tenant)",
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Product name",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Product description (can be rich text/HTML)",
    )

    # Inventory
    units_in_stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Packaged units ready to ship",
    )

    # Packaging - can be manual cost or linked to consumable
    packaging_cost: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        server_default="0",
        comment="Manual packaging cost per product (used if no consumable linked)",
    )

    packaging_consumable_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("consumable_types.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional consumable used for packaging (e.g., box)",
    )

    packaging_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Quantity of packaging consumable per product",
    )

    assembly_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Time to assemble/package in minutes",
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether product is active for sale",
    )

    # Shop visibility (separate from is_active for internal tracking)
    shop_visible: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
        comment="Whether product appears in the online shop",
    )

    # Shop-specific description (can differ from internal description)
    shop_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Rich HTML description for shop display (falls back to description if null)",
    )

    # Featured/showcase fields (for dragons, special editions)
    is_featured: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
        comment="Whether product is featured in showcase/gallery",
    )

    # Dragon flag - separate from is_featured for shop dragon collection
    is_dragon: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
        comment="Whether product appears in the Dragons collection",
    )

    # Print-to-order flag (made to order vs in-stock)
    print_to_order: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether product is printed to order (vs in-stock ready to ship)",
    )

    # Shipping
    free_shipping: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether product qualifies for free shipping",
    )

    feature_title: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Custom title for featured display (e.g., dragon name)",
    )

    backstory: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Backstory/lore for featured items (dragons, special editions)",
    )

    # Review statistics (cached for performance)
    average_rating: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(3, 2),
        nullable=True,
        comment="Average review rating (1.00-5.00), null if no reviews",
    )
    review_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of approved reviews",
    )

    # Full-text search vector (PostgreSQL only, auto-updated by trigger)
    # Uses TSVectorType which falls back to TEXT for SQLite testing
    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVectorType,
        nullable=True,
        comment="Full-text search vector (auto-populated by PostgreSQL trigger)",
    )

    # Relationships
    product_models: Mapped[list["ProductModel"]] = relationship(
        "ProductModel",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    pricing: Mapped[list["ProductPricing"]] = relationship(
        "ProductPricing",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    images: Mapped[list["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ProductImage.display_order",
    )

    categories: Mapped[list["Category"]] = relationship(
        "Category",
        secondary="product_categories",
        back_populates="products",
        lazy="selectin",
    )

    packaging_consumable: Mapped[Optional["ConsumableType"]] = relationship(
        "ConsumableType",
        foreign_keys=[packaging_consumable_id],
        lazy="selectin",
    )

    # Composite product relationships (Product -> Product)
    # child_products: Products that this product contains (I am the parent/bundle)
    child_products: Mapped[list["ProductComponent"]] = relationship(
        "ProductComponent",
        foreign_keys="[ProductComponent.parent_product_id]",
        back_populates="parent_product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # parent_products: Products that contain this product (I am a child/component)
    parent_products: Mapped[list["ProductComponent"]] = relationship(
        "ProductComponent",
        foreign_keys="[ProductComponent.child_product_id]",
        back_populates="child_product",
        lazy="selectin",
    )

    # Production runs making this product
    production_runs: Mapped[list["ProductionRun"]] = relationship(
        "ProductionRun",
        back_populates="product",
        lazy="select",
    )

    # Designer relationship
    designer: Mapped[Optional["Designer"]] = relationship(
        "Designer",
        back_populates="products",
        lazy="selectin",
    )

    # Reviews
    reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="noload",  # Don't auto-load reviews, use explicit query
    )

    # Print queue jobs
    print_jobs: Mapped[List["PrintJob"]] = relationship(
        "PrintJob",
        back_populates="product",
        lazy="select",
    )

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_product_tenant_sku"),
        # GIN index for full-text search (PostgreSQL only)
        Index(
            "ix_products_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        {"comment": "Sellable products composed of one or more printed models"},
    )

    def __repr__(self) -> str:
        return f"<Product(sku={self.sku}, name={self.name})>"

    def calculate_make_cost(self, labor_rate: float = 10.0, visited: set | None = None) -> dict:
        """
        Calculate the make cost for this product.

        Supports composite products (bundles) by recursively calculating costs
        for child products. Includes cycle detection to prevent infinite loops.

        Args:
            labor_rate: Hourly labor rate (default £10/hr)
            visited: Set of product IDs already visited (for cycle detection)

        Returns:
            dict with cost breakdown:
            - models_cost: Sum of (model.cost × quantity) for all models
            - child_products_cost: Sum of child product costs × quantity
            - packaging_cost: Packaging cost
            - assembly_cost: Assembly labor cost
            - total_make_cost: Total cost to make this product

        Raises:
            ValueError: If circular reference detected in product hierarchy
        """
        # Initialize visited set for cycle detection
        if visited is None:
            visited = set()

        # Check for circular reference
        if self.id in visited:
            raise ValueError(
                f"Circular reference detected: Product {self.sku} appears in its own hierarchy"
            )
        visited.add(self.id)

        models_cost = Decimal("0")
        child_products_cost = Decimal("0")

        # Calculate cost of direct models (printed items)
        for pm in self.product_models:
            if pm.model:
                # Get model cost (materials + components + labor + overhead)
                model_cost = self._calculate_model_cost(pm.model, labor_rate)
                models_cost += model_cost * pm.quantity

        # Calculate cost of child products (composite/bundles)
        for pc in self.child_products:
            if pc.child_product:
                # Recursively calculate child product cost with visited copy
                child_cost_breakdown = pc.child_product.calculate_make_cost(
                    labor_rate=labor_rate, visited=visited.copy()
                )
                child_products_cost += (
                    Decimal(str(child_cost_breakdown["total_make_cost"])) * pc.quantity
                )

        assembly_cost = Decimal(str(self.assembly_minutes)) / 60 * Decimal(str(labor_rate))

        # Get packaging cost (from consumable or manual)
        if self.packaging_consumable and self.packaging_consumable.unit_cost:
            packaging = Decimal(str(self.packaging_consumable.unit_cost)) * self.packaging_quantity
        else:
            packaging = Decimal(str(self.packaging_cost))

        total_make_cost = models_cost + child_products_cost + packaging + assembly_cost

        return {
            "models_cost": float(models_cost),
            "child_products_cost": float(child_products_cost),
            "packaging_cost": float(packaging),
            "assembly_cost": float(assembly_cost),
            "total_make_cost": float(total_make_cost),
        }

    def _calculate_model_cost(self, model, labor_rate: float) -> Decimal:
        """Calculate cost for a single model."""
        # Materials cost
        materials_cost = sum(
            Decimal(str(m.weight_grams)) * Decimal(str(m.cost_per_gram)) for m in model.materials
        )

        # Components cost
        components_cost = sum(
            Decimal(str(c.quantity)) * Decimal(str(c.unit_cost)) for c in model.components
        )

        # Labor cost
        rate = float(model.labor_rate_override) if model.labor_rate_override else labor_rate
        labor_cost = Decimal(str(model.labor_hours)) * Decimal(str(rate))

        # Subtotal before overhead
        subtotal = materials_cost + components_cost + labor_cost

        # Overhead
        overhead_pct = Decimal(str(model.overhead_percentage)) / 100
        overhead_cost = subtotal * overhead_pct

        return subtotal + overhead_cost
