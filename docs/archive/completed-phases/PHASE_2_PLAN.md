# Phase 2 Implementation Plan: Product Catalog & Costing

**Timeline**: 2-3 weeks (20-30 hours)
**Status**: Ready to start
**Dependencies**: Phase 1 Complete ✅

---

## 📋 Overview

Phase 2 builds on the inventory management foundation to add:
- Product catalog with SKUs
- Multi-material Bill of Materials (BOM)
- Component cost tracking (magnets, inserts, screws, etc.)
- Automatic cost calculation engine
- Labor and overhead allocation

---

## 🎯 Success Criteria

- [ ] Can create products with SKUs and descriptions
- [ ] Can add multiple materials to a product (BOM)
- [ ] Can add non-material components (magnets, inserts, etc.)
- [ ] Cost calculation automatically updates when materials/components change
- [ ] Can configure labor rate and overhead percentage
- [ ] Product list displays with calculated costs
- [ ] Multi-tenant isolation verified
- [ ] All tests pass (80%+ coverage)

---

## 📊 Database Schema Changes

### New Tables

**products**
- id (UUID, PK)
- tenant_id (UUID, FK → tenants)
- sku (VARCHAR, unique per tenant)
- name (VARCHAR)
- description (TEXT)
- category (VARCHAR)
- image_url (VARCHAR, nullable)
- labor_hours (DECIMAL, default 0)
- labor_rate_override (DECIMAL, nullable) - per-product rate if different from tenant default
- overhead_percentage (DECIMAL, default 0)
- created_at, updated_at

**product_materials** (BOM - Bill of Materials)
- id (UUID, PK)
- product_id (UUID, FK → products)
- spool_id (UUID, FK → spools) - which material/spool
- weight_grams (DECIMAL) - how much of this material is used
- cost_per_gram (DECIMAL) - snapshot at time of adding (for historical accuracy)
- created_at

**product_components** (non-material costs)
- id (UUID, PK)
- product_id (UUID, FK → products)
- component_name (VARCHAR) - "M3 magnet", "heat insert", etc.
- quantity (INT)
- unit_cost (DECIMAL)
- supplier (VARCHAR, nullable)
- created_at

**tenant_settings** (add columns to existing tenants table or create new table)
- default_labor_rate (DECIMAL) - $/hour
- default_overhead_percentage (DECIMAL) - % of material+labor

---

## 🔧 Backend Implementation

### Models (app/models/)

**product.py**
```python
class Product(Base):
    __tablename__ = "products"

    id = Column(UUID, primary_key=True, default=uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.id"), nullable=False)
    sku = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)
    image_url = Column(String)
    labor_hours = Column(Numeric(10, 2), default=0)
    labor_rate_override = Column(Numeric(10, 2))
    overhead_percentage = Column(Numeric(5, 2), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    materials = relationship("ProductMaterial", back_populates="product")
    components = relationship("ProductComponent", back_populates="product")

    # Unique constraint: SKU per tenant
    __table_args__ = (
        UniqueConstraint('tenant_id', 'sku', name='unique_sku_per_tenant'),
        Index('idx_products_tenant', 'tenant_id'),
    )
```

**product_material.py**
```python
class ProductMaterial(Base):
    __tablename__ = "product_materials"

    id = Column(UUID, primary_key=True, default=uuid4)
    product_id = Column(UUID, ForeignKey("products.id"), nullable=False)
    spool_id = Column(UUID, ForeignKey("spools.id"), nullable=False)
    weight_grams = Column(Numeric(10, 2), nullable=False)
    cost_per_gram = Column(Numeric(10, 4), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="materials")
    spool = relationship("Spool")
```

**product_component.py**
```python
class ProductComponent(Base):
    __tablename__ = "product_components"

    id = Column(UUID, primary_key=True, default=uuid4)
    product_id = Column(UUID, ForeignKey("products.id"), nullable=False)
    component_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(10, 2), nullable=False)
    supplier = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    product = relationship("Product", back_populates="components")
```

### Schemas (app/schemas/)

**product.py**
```python
class ProductBase(BaseModel):
    sku: str
    name: str
    description: str | None = None
    category: str | None = None
    image_url: str | None = None
    labor_hours: Decimal = Decimal("0")
    labor_rate_override: Decimal | None = None
    overhead_percentage: Decimal = Decimal("0")

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    # ... all fields optional

class ProductMaterialOut(BaseModel):
    id: UUID
    spool_id: UUID
    weight_grams: Decimal
    cost_per_gram: Decimal
    # Include spool details (material, color, brand)
    spool: SpoolOut

class ProductComponentOut(BaseModel):
    id: UUID
    component_name: str
    quantity: int
    unit_cost: Decimal
    supplier: str | None

class ProductCostBreakdown(BaseModel):
    material_cost: Decimal
    component_cost: Decimal
    labor_cost: Decimal
    overhead_cost: Decimal
    total_cost: Decimal

class ProductOut(ProductBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    materials: list[ProductMaterialOut] = []
    components: list[ProductComponentOut] = []
    cost_breakdown: ProductCostBreakdown
```

### Services (app/services/)

**costing.py**
```python
class CostingService:
    """Calculate product costs."""

    @staticmethod
    def calculate_product_cost(
        product: Product,
        tenant_default_labor_rate: Decimal = Decimal("0"),
        tenant_default_overhead_pct: Decimal = Decimal("0")
    ) -> ProductCostBreakdown:
        """Calculate total product cost."""

        # Material cost
        material_cost = sum(
            mat.weight_grams * mat.cost_per_gram
            for mat in product.materials
        )

        # Component cost
        component_cost = sum(
            comp.quantity * comp.unit_cost
            for comp in product.components
        )

        # Labor cost
        labor_rate = product.labor_rate_override or tenant_default_labor_rate
        labor_cost = product.labor_hours * labor_rate

        # Overhead cost
        overhead_pct = product.overhead_percentage or tenant_default_overhead_pct
        overhead_base = material_cost + labor_cost
        overhead_cost = overhead_base * (overhead_pct / 100)

        total_cost = material_cost + component_cost + labor_cost + overhead_cost

        return ProductCostBreakdown(
            material_cost=material_cost,
            component_cost=component_cost,
            labor_cost=labor_cost,
            overhead_cost=overhead_cost,
            total_cost=total_cost
        )
```

### API Endpoints (app/api/v1/products.py)

```python
@router.get("/", response_model=list[ProductOut])
async def list_products(
    skip: int = 0,
    limit: int = 100,
    category: str | None = None,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """List all products for current tenant."""
    # Query with filters, calculate costs for each
    pass

@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: UUID,
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Get product detail with cost breakdown."""
    pass

@router.post("/", response_model=ProductOut, status_code=201)
async def create_product(
    product: ProductCreate,
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Create new product."""
    pass

@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: UUID,
    product: ProductUpdate,
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Update existing product."""
    pass

@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: UUID,
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Delete product (soft delete recommended)."""
    pass

# BOM Management
@router.post("/{product_id}/materials", response_model=ProductMaterialOut, status_code=201)
async def add_product_material(
    product_id: UUID,
    material: ProductMaterialCreate,
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Add material to product BOM."""
    pass

@router.delete("/{product_id}/materials/{material_id}", status_code=204)
async def remove_product_material(
    product_id: UUID,
    material_id: UUID,
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Remove material from product BOM."""
    pass

# Component Management
@router.post("/{product_id}/components", response_model=ProductComponentOut, status_code=201)
async def add_product_component(
    product_id: UUID,
    component: ProductComponentCreate,
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Add component to product."""
    pass

@router.delete("/{product_id}/components/{component_id}", status_code=204)
async def remove_product_component(
    product_id: UUID,
    component_id: UUID,
    current_user: User = Depends(get_current_user),
    current_tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db)
):
    """Remove component from product."""
    pass
```

---

## 🎨 Frontend Implementation

### API Client (src/lib/api/products.ts)

```typescript
export interface Product {
  id: string
  tenantId: string
  sku: string
  name: string
  description?: string
  category?: string
  imageUrl?: string
  laborHours: number
  laborRateOverride?: number
  overheadPercentage: number
  materials: ProductMaterial[]
  components: ProductComponent[]
  costBreakdown: CostBreakdown
  createdAt: string
  updatedAt: string
}

export interface ProductMaterial {
  id: string
  spoolId: string
  weightGrams: number
  costPerGram: number
  spool: Spool
}

export interface ProductComponent {
  id: string
  componentName: string
  quantity: number
  unitCost: number
  supplier?: string
}

export interface CostBreakdown {
  materialCost: number
  componentCost: number
  laborCost: number
  overheadCost: number
  totalCost: number
}

// API functions
export const listProducts = async (filters?: ProductFilters): Promise<Product[]> => {
  // Implementation
}

export const getProduct = async (id: string): Promise<Product> => {
  // Implementation
}

export const createProduct = async (data: ProductCreate): Promise<Product> => {
  // Implementation
}

export const updateProduct = async (id: string, data: ProductUpdate): Promise<Product> => {
  // Implementation
}

export const deleteProduct = async (id: string): Promise<void> => {
  // Implementation
}

// BOM management
export const addProductMaterial = async (productId: string, data: ProductMaterialCreate): Promise<ProductMaterial> => {
  // Implementation
}

export const removeProductMaterial = async (productId: string, materialId: string): Promise<void> => {
  // Implementation
}

// Component management
export const addProductComponent = async (productId: string, data: ProductComponentCreate): Promise<ProductComponent> => {
  // Implementation
}

export const removeProductComponent = async (productId: string, componentId: string): Promise<void> => {
  // Implementation
}
```

### Components

**src/components/products/ProductList.tsx**
- Data table with search, sort, filter by category
- Columns: SKU, Name, Category, Total Cost, Materials Count
- Actions: View, Edit, Delete
- Click row to navigate to detail page

**src/components/products/ProductDetail.tsx**
- Display product info
- Materials list (BOM) with weights and costs
- Components list with quantities and costs
- Cost breakdown visualization (stacked bar chart or pie chart)
- Edit and Delete buttons

**src/components/products/ProductForm.tsx**
- SKU input (auto-suggest format based on category)
- Name, description, category dropdowns
- Image upload (Phase 2+)
- Labor hours input
- Labor rate override (optional)
- Overhead percentage input
- Form validation

**src/components/products/BOMEditor.tsx**
- Multi-material selector (dropdown of tenant's spools)
- Weight input per material
- Display cost per gram from spool
- Display total material cost
- Add/Remove material buttons
- Drag-to-reorder materials (optional enhancement)

**src/components/products/ComponentsEditor.tsx**
- Component name input
- Quantity input
- Unit cost input
- Supplier input (optional)
- Add/Remove component buttons
- Total component cost display

**src/components/products/CostBreakdownCard.tsx**
- Material cost (with breakdown per material)
- Component cost (with breakdown per component)
- Labor cost (hours × rate)
- Overhead cost (percentage of material+labor)
- **Total cost** (prominent display)
- Visual chart (Recharts bar/pie chart)

### Pages/Routes

**src/routes/products/index.tsx**
- ProductList component
- "New Product" button → navigate to /products/new

**src/routes/products/new.tsx**
- ProductForm component
- BOMEditor component
- ComponentsEditor component
- Real-time cost calculation preview

**src/routes/products/$productId.tsx**
- ProductDetail component
- "Edit" button → edit mode or navigate to /products/$productId/edit

**src/routes/products/$productId/edit.tsx**
- ProductForm (pre-filled)
- BOMEditor (pre-filled)
- ComponentsEditor (pre-filled)
- Real-time cost recalculation

### Hooks (src/hooks/useProducts.ts)

```typescript
export const useProducts = (filters?: ProductFilters) => {
  return useQuery({
    queryKey: ['products', filters],
    queryFn: () => listProducts(filters),
  })
}

export const useProduct = (id: string) => {
  return useQuery({
    queryKey: ['products', id],
    queryFn: () => getProduct(id),
  })
}

export const useCreateProduct = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

export const useUpdateProduct = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ProductUpdate }) =>
      updateProduct(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
      queryClient.invalidateQueries({ queryKey: ['products', id] })
    },
  })
}

export const useDeleteProduct = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteProduct,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['products'] })
    },
  })
}

// Similar hooks for BOM and components
```

---

## 🧪 Testing Strategy

### Backend Tests (pytest)

**test_products_crud.py**
- Test create product with valid data
- Test create product with duplicate SKU (same tenant) → 400
- Test create product with duplicate SKU (different tenant) → OK
- Test list products filtered by category
- Test get product includes cost breakdown
- Test update product recalculates cost
- Test delete product
- Test multi-tenant isolation

**test_costing.py**
- Test material cost calculation
- Test component cost calculation
- Test labor cost with default rate
- Test labor cost with override rate
- Test overhead calculation
- Test total cost = sum of all parts
- Test cost updates when BOM changes

**test_bom.py**
- Test add material to product
- Test remove material from product
- Test cost per gram snapshot at time of adding
- Test add component to product
- Test remove component from product

### Frontend Tests (Vitest + Testing Library)

**ProductList.test.tsx**
- Renders list of products
- Filters by category
- Searches by name/SKU
- Navigates to detail on click

**ProductForm.test.tsx**
- Validates required fields
- Submits valid product
- Displays error messages

**BOMEditor.test.tsx**
- Adds material to BOM
- Removes material from BOM
- Updates cost when material added/removed

**CostBreakdownCard.test.tsx**
- Displays all cost components
- Highlights total cost
- Shows chart visualization

---

## 📦 Deployment Steps

1. Create and test migrations locally
   ```bash
   cd backend
   poetry run alembic revision --autogenerate -m "Add products, materials, components tables"
   poetry run alembic upgrade head
   ```

2. Build and push Docker images
   ```bash
   # Backend
   cd backend
   docker buildx build --platform linux/amd64 -t batchivo-backend:v2.0 --load .
   docker tag batchivo-backend:v2.0 192.168.98.138:30500/batchivo-backend:v2.0
   docker push 192.168.98.138:30500/batchivo-backend:v2.0

   # Frontend
   cd frontend
   docker buildx build --platform linux/amd64 -t batchivo-frontend:v2.0 --load .
   docker tag batchivo-frontend:v2.0 192.168.98.138:30500/batchivo-frontend:v2.0
   docker push 192.168.98.138:30500/batchivo-frontend:v2.0
   ```

3. Update k8s deployments
   ```bash
   kubectl set image deployment/backend backend=192.168.98.138:30500/batchivo-backend:v2.0 -n batchivo
   kubectl set image deployment/frontend frontend=192.168.98.138:30500/batchivo-frontend:v2.0 -n batchivo
   ```

4. Verify deployment
   ```bash
   kubectl rollout status deployment/backend -n batchivo
   kubectl rollout status deployment/frontend -n batchivo
   curl https://api.batchivo.com/health
   ```

---

## 📅 Implementation Schedule

**Week 1: Backend Foundation**
- Days 1-2: Database models + migrations
- Days 3-4: API endpoints (CRUD)
- Days 5-7: Cost calculation service + tests

**Week 2: Frontend Core**
- Days 1-2: Product list + detail pages
- Days 3-4: Product form + validation
- Days 5-7: BOM editor + real-time cost preview

**Week 3: Polish & Deploy**
- Days 1-2: Components editor + cost breakdown UI
- Days 3-4: Testing (integration + E2E)
- Days 5-6: Deployment to k3s
- Day 7: Documentation + verification

---

## 🎉 Expected Outcomes

By end of Phase 2:
- Complete product catalog system
- Multi-material BOM support
- Accurate cost calculation
- Professional UI for product management
- Foundation for Phase 3 (Pricing Engine)

**Phase 3 Preview**: Multi-marketplace pricing will build on Phase 2's cost data to calculate selling prices across different platforms (Etsy, eBay, local fairs) with platform-specific fee structures.

---

*Last Updated: 2025-11-06*
*Status: Ready to Start*
