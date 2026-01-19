"""Costing service for calculating model and product costs."""

from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

if TYPE_CHECKING:
    from app.models.model import Model
    from app.models.product import Product

from app.schemas.model import CostBreakdown
from app.schemas.product import ProductCostBreakdown


class CircularReferenceError(Exception):
    """Raised when a circular reference is detected in product components."""

    def __init__(self, product_id: UUID, visited: set):
        self.product_id = product_id
        self.visited = visited
        super().__init__(
            f"Circular reference detected: Product {product_id} already visited. "
            f"Chain: {' -> '.join(str(v) for v in visited)}"
        )


class MaxDepthExceededError(Exception):
    """Raised when product hierarchy exceeds maximum allowed depth."""

    def __init__(self, depth: int, max_depth: int):
        self.depth = depth
        self.max_depth = max_depth
        super().__init__(
            f"Product hierarchy too deep: depth {depth} exceeds maximum {max_depth}. "
            f"Consider flattening the product structure."
        )


# Default labor rate (£10/hour)
DEFAULT_LABOR_RATE = Decimal("10.00")

# Maximum recursion depth for product cost calculation
MAX_RECURSION_DEPTH = 20


class CostingService:
    """Service for calculating model and product costs."""

    @staticmethod
    def calculate_model_cost(
        model: "Model",
        tenant_default_labor_rate: Optional[Decimal] = None,
        tenant_default_overhead_pct: Optional[Decimal] = None,
    ) -> CostBreakdown:
        """
        Calculate total model (printed item) cost with breakdown.

        Args:
            model: Model instance with materials and components loaded
            tenant_default_labor_rate: Default labor rate from tenant settings (£/hour)
            tenant_default_overhead_pct: Default overhead percentage from tenant settings (0-100)

        Returns:
            CostBreakdown with material, component, labor, overhead, and total costs
        """
        # Default values if not provided
        if tenant_default_labor_rate is None:
            tenant_default_labor_rate = DEFAULT_LABOR_RATE
        if tenant_default_overhead_pct is None:
            tenant_default_overhead_pct = Decimal("0")

        # Get prints per plate (for batch printing cost division)
        prints_per_plate = (
            Decimal(str(model.prints_per_plate))
            if model.prints_per_plate and model.prints_per_plate > 0
            else Decimal("1")
        )

        # 1. Calculate material cost (sum of all materials in BOM)
        # Note: weight_grams is the TOTAL plate weight, we divide by prints_per_plate for per-unit cost
        material_cost = Decimal("0")
        if hasattr(model, "materials"):
            for material in model.materials:
                plate_cost = Decimal(str(material.weight_grams)) * Decimal(
                    str(material.cost_per_gram)
                )
                material_cost += plate_cost / prints_per_plate

        # 2. Calculate component cost (sum of all components)
        component_cost = Decimal("0")
        if hasattr(model, "components"):
            for component in model.components:
                component_cost += Decimal(str(component.quantity)) * Decimal(
                    str(component.unit_cost)
                )

        # 3. Calculate labor cost
        labor_rate = (
            Decimal(str(model.labor_rate_override))
            if model.labor_rate_override is not None
            else tenant_default_labor_rate
        )
        labor_hours = Decimal(str(model.labor_hours)) if model.labor_hours else Decimal("0")
        labor_cost = labor_hours * labor_rate

        # 4. Calculate overhead cost (percentage of material + labor)
        overhead_pct = (
            Decimal(str(model.overhead_percentage))
            if model.overhead_percentage and model.overhead_percentage > 0
            else tenant_default_overhead_pct
        )
        overhead_base = material_cost + labor_cost
        overhead_cost = overhead_base * (overhead_pct / Decimal("100"))

        # 5. Calculate total cost
        total_cost = material_cost + component_cost + labor_cost + overhead_cost

        return CostBreakdown(
            material_cost=material_cost.quantize(Decimal("0.001")),
            component_cost=component_cost.quantize(Decimal("0.001")),
            labor_cost=labor_cost.quantize(Decimal("0.001")),
            overhead_cost=overhead_cost.quantize(Decimal("0.001")),
            total_cost=total_cost.quantize(Decimal("0.001")),
        )

    @staticmethod
    def calculate_product_cost(
        product: "Product",
        labor_rate: Optional[Decimal] = None,
        _visited: Optional[set] = None,
        _depth: int = 0,
    ) -> ProductCostBreakdown:
        """
        Calculate total product (sellable item) cost with breakdown.

        Supports nested products (bundles containing other products) with
        recursive cost calculation and circular reference detection.

        Args:
            product: Product instance with product_models and child_products loaded
            labor_rate: Labor rate (£/hour), defaults to DEFAULT_LABOR_RATE
            _visited: Internal set for cycle detection (do not pass manually)
            _depth: Internal recursion depth counter (do not pass manually)

        Returns:
            ProductCostBreakdown with models cost, child products cost, packaging,
            assembly, and total make cost

        Raises:
            CircularReferenceError: If a circular reference is detected in product hierarchy
            MaxDepthExceededError: If product hierarchy exceeds MAX_RECURSION_DEPTH
        """
        if labor_rate is None:
            labor_rate = DEFAULT_LABOR_RATE

        # Check recursion depth limit
        if _depth > MAX_RECURSION_DEPTH:
            raise MaxDepthExceededError(_depth, MAX_RECURSION_DEPTH)

        # Initialize visited set for cycle detection
        if _visited is None:
            _visited = set()

        # Check for circular reference
        if product.id in _visited:
            raise CircularReferenceError(product.id, _visited)

        # Add current product to visited set
        _visited = _visited.copy()  # Create copy to not affect sibling branches
        _visited.add(product.id)

        # 1. Calculate total model cost (sum of all models × quantity × model unit cost)
        # Phase 3: Also track actual production costs from models
        models_cost = Decimal("0")
        models_actual_cost = Decimal("0")
        models_with_actual_cost = 0
        models_total = 0
        seen_model_ids: set = set()

        if hasattr(product, "product_models"):
            for pm in product.product_models:
                if hasattr(pm, "model") and pm.model:
                    # Calculate model's unit cost (BOM-based theoretical)
                    model_cost = CostingService.calculate_model_cost(pm.model)
                    models_cost += Decimal(str(pm.quantity)) * model_cost.total_cost

                    # Track unique models for actual cost calculation
                    if pm.model.id not in seen_model_ids:
                        seen_model_ids.add(pm.model.id)
                        models_total += 1

                        # Phase 3: Add actual production cost if available
                        if pm.model.actual_production_cost is not None:
                            models_actual_cost += Decimal(str(pm.quantity)) * Decimal(
                                str(pm.model.actual_production_cost)
                            )
                            models_with_actual_cost += 1
                    elif pm.model.actual_production_cost is not None:
                        # Same model appears multiple times - just add the cost
                        models_actual_cost += Decimal(str(pm.quantity)) * Decimal(
                            str(pm.model.actual_production_cost)
                        )

        # 2. Calculate total child product cost (for bundles)
        # This is recursive - child products may contain other products
        child_products_cost = Decimal("0")
        if hasattr(product, "child_products"):
            for pc in product.child_products:
                if hasattr(pc, "child_product") and pc.child_product:
                    # Recursively calculate child product's cost
                    child_cost = CostingService.calculate_product_cost(
                        pc.child_product,
                        labor_rate=labor_rate,
                        _visited=_visited,
                        _depth=_depth + 1,
                    )
                    child_products_cost += Decimal(str(pc.quantity)) * child_cost.total_make_cost

        # 3. Packaging cost - use consumable cost if linked, otherwise manual cost
        if hasattr(product, "packaging_consumable") and product.packaging_consumable:
            consumable = product.packaging_consumable
            unit_cost = (
                Decimal(str(consumable.current_cost_per_unit))
                if consumable.current_cost_per_unit
                else Decimal("0")
            )
            quantity = product.packaging_quantity if product.packaging_quantity else 1
            packaging_cost = unit_cost * Decimal(str(quantity))
        else:
            packaging_cost = (
                Decimal(str(product.packaging_cost)) if product.packaging_cost else Decimal("0")
            )

        # 4. Assembly cost (minutes to hours × labor rate)
        assembly_minutes = (
            Decimal(str(product.assembly_minutes)) if product.assembly_minutes else Decimal("0")
        )
        assembly_hours = assembly_minutes / Decimal("60")
        assembly_cost = assembly_hours * labor_rate

        # 5. Total make cost (now includes child products cost)
        total_make_cost = models_cost + child_products_cost + packaging_cost + assembly_cost

        # 6. Phase 3: Calculate actual total cost and variance if we have actual data
        total_actual_cost = None
        cost_variance_percentage = None

        if models_with_actual_cost > 0 and models_total > 0:
            # Only calculate total actual cost if ALL models have actual data
            if models_with_actual_cost == models_total:
                total_actual_cost = (
                    models_actual_cost + child_products_cost + packaging_cost + assembly_cost
                )
                # Calculate variance: (actual - theoretical) / theoretical * 100
                if total_make_cost > 0:
                    cost_variance_percentage = (
                        (total_actual_cost - total_make_cost) / total_make_cost * Decimal("100")
                    )

        return ProductCostBreakdown(
            models_cost=models_cost.quantize(Decimal("0.01")),
            child_products_cost=child_products_cost.quantize(Decimal("0.01")),
            packaging_cost=packaging_cost.quantize(Decimal("0.01")),
            assembly_cost=assembly_cost.quantize(Decimal("0.01")),
            total_make_cost=total_make_cost.quantize(Decimal("0.01")),
            # Phase 3 fields
            models_actual_cost=models_actual_cost.quantize(Decimal("0.01"))
            if models_with_actual_cost > 0
            else None,
            total_actual_cost=total_actual_cost.quantize(Decimal("0.01"))
            if total_actual_cost is not None
            else None,
            cost_variance_percentage=cost_variance_percentage.quantize(Decimal("0.01"))
            if cost_variance_percentage is not None
            else None,
            models_with_actual_cost=models_with_actual_cost,
            models_total=models_total,
        )

    @staticmethod
    def calculate_profit(
        list_price: Decimal,
        make_cost: Decimal,
        fee_percentage: Decimal = Decimal("0"),
        fee_fixed: Decimal = Decimal("0"),
    ) -> dict:
        """
        Calculate profit and margin for a product at a given price.

        Args:
            list_price: Selling price
            make_cost: Total make cost
            fee_percentage: Platform percentage fee (0-100)
            fee_fixed: Fixed platform fee per transaction

        Returns:
            Dict with platform_fee, net_revenue, profit, margin_percentage
        """
        # Calculate platform fees
        percentage_fee = list_price * (fee_percentage / Decimal("100"))
        platform_fee = percentage_fee + fee_fixed

        # Net revenue after platform takes their cut
        net_revenue = list_price - platform_fee

        # Profit after deducting make cost
        profit = net_revenue - make_cost

        # Margin percentage (profit / list_price * 100)
        margin_percentage = (
            (profit / list_price * Decimal("100")) if list_price > 0 else Decimal("0")
        )

        return {
            "platform_fee": platform_fee.quantize(Decimal("0.01")),
            "net_revenue": net_revenue.quantize(Decimal("0.01")),
            "profit": profit.quantize(Decimal("0.01")),
            "margin_percentage": margin_percentage.quantize(Decimal("0.01")),
        }

    @staticmethod
    def calculate_cost_per_gram_from_spool(
        purchase_price: Optional[Decimal],
        initial_weight: Decimal,
    ) -> Decimal:
        """
        Calculate cost per gram from spool purchase information.

        Args:
            purchase_price: Purchase price of spool
            initial_weight: Initial weight of spool in grams

        Returns:
            Cost per gram
        """
        if purchase_price is None or purchase_price <= 0:
            return Decimal("0")

        if initial_weight <= 0:
            return Decimal("0")

        return (Decimal(str(purchase_price)) / Decimal(str(initial_weight))).quantize(
            Decimal("0.0001")
        )
