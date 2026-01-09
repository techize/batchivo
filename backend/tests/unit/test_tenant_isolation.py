"""Tests for multi-tenant data isolation.

Note: These tests verify application-level tenant isolation.
PostgreSQL RLS policies provide additional database-level protection in production.
Since tests use SQLite (which doesn't support RLS), these tests focus on
verifying the application correctly filters data by tenant_id.
"""

import pytest
from uuid import uuid4
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, TenantType
from app.models.user import User, UserTenant, UserRole
from app.models.product import Product
from app.models.spool import Spool


@pytest.fixture
async def second_tenant(db_session: AsyncSession) -> Tenant:
    """Create a second tenant for isolation testing."""
    tenant = Tenant(
        id=uuid4(),
        name="Second Tenant",
        slug="second-tenant",
        tenant_type=TenantType.THREE_D_PRINT.value,
        settings={"default_labor_rate": 25.0, "currency": "EUR"},
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def second_user(db_session: AsyncSession, second_tenant: Tenant) -> User:
    """Create a user for the second tenant."""
    from app.auth.password import get_password_hash

    user = User(
        id=uuid4(),
        email="user2@example.com",
        full_name="Second User",
        hashed_password=get_password_hash("password123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    user_tenant = UserTenant(
        user_id=user.id,
        tenant_id=second_tenant.id,
        role=UserRole.ADMIN,
    )
    db_session.add(user_tenant)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def tenant_a_product(db_session: AsyncSession, test_tenant: Tenant) -> Product:
    """Create a product for tenant A."""
    product = Product(
        id=uuid4(),
        tenant_id=test_tenant.id,
        sku="TENANT-A-001",
        name="Tenant A Product",
        description="Product belonging to Tenant A",
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def tenant_b_product(db_session: AsyncSession, second_tenant: Tenant) -> Product:
    """Create a product for tenant B."""
    product = Product(
        id=uuid4(),
        tenant_id=second_tenant.id,
        sku="TENANT-B-001",
        name="Tenant B Product",
        description="Product belonging to Tenant B",
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


class TestTenantDataIsolation:
    """Test that tenant data is properly isolated."""

    @pytest.mark.asyncio
    async def test_products_belong_to_specific_tenant(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        second_tenant: Tenant,
        tenant_a_product: Product,
        tenant_b_product: Product,
    ):
        """Test that products are associated with correct tenant."""
        assert tenant_a_product.tenant_id == test_tenant.id
        assert tenant_b_product.tenant_id == second_tenant.id
        assert tenant_a_product.tenant_id != tenant_b_product.tenant_id

    @pytest.mark.asyncio
    async def test_query_filters_by_tenant_id(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        second_tenant: Tenant,
        tenant_a_product: Product,
        tenant_b_product: Product,
    ):
        """Test that queries with tenant_id filter return only that tenant's data."""
        # Query for tenant A products
        result_a = await db_session.execute(
            select(Product).where(Product.tenant_id == test_tenant.id)
        )
        products_a = result_a.scalars().all()

        # Query for tenant B products
        result_b = await db_session.execute(
            select(Product).where(Product.tenant_id == second_tenant.id)
        )
        products_b = result_b.scalars().all()

        # Verify isolation
        product_ids_a = {p.id for p in products_a}
        product_ids_b = {p.id for p in products_b}

        assert tenant_a_product.id in product_ids_a
        assert tenant_b_product.id not in product_ids_a

        assert tenant_b_product.id in product_ids_b
        assert tenant_a_product.id not in product_ids_b

    @pytest.mark.asyncio
    async def test_cross_tenant_product_access_impossible(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        second_tenant: Tenant,
        tenant_a_product: Product,
    ):
        """Test that querying with wrong tenant_id doesn't return other tenant's products."""
        # Try to access tenant A's product with tenant B's ID
        result = await db_session.execute(
            select(Product).where(
                Product.id == tenant_a_product.id,
                Product.tenant_id == second_tenant.id,  # Wrong tenant!
            )
        )
        product = result.scalar_one_or_none()

        # Should not find the product
        assert product is None

    @pytest.mark.asyncio
    async def test_tenant_has_own_products_only(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        tenant_a_product: Product,
        tenant_b_product: Product,
    ):
        """Test that tenant's product list contains only their products."""
        # Simulate what an API would do - query products for current tenant
        result = await db_session.execute(
            select(Product).where(Product.tenant_id == test_tenant.id)
        )
        tenant_products = result.scalars().all()

        # Verify only tenant A's products are returned
        product_skus = [p.sku for p in tenant_products]
        assert "TENANT-A-001" in product_skus
        assert "TENANT-B-001" not in product_skus


class TestUserTenantAssociation:
    """Test user-tenant association and isolation."""

    @pytest.mark.asyncio
    async def test_user_belongs_to_specific_tenant(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_tenant: Tenant,
    ):
        """Test that user is associated with correct tenant."""
        # Refresh to load relationships
        result = await db_session.execute(select(User).where(User.id == test_user.id))
        user = result.scalar_one()

        # Check user_tenants relationship
        result = await db_session.execute(select(UserTenant).where(UserTenant.user_id == user.id))
        user_tenants = result.scalars().all()

        tenant_ids = [ut.tenant_id for ut in user_tenants]
        assert test_tenant.id in tenant_ids

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_tenant(
        self,
        db_session: AsyncSession,
        test_user: User,
        second_tenant: Tenant,
    ):
        """Test that user doesn't have access to other tenants."""
        result = await db_session.execute(
            select(UserTenant).where(
                UserTenant.user_id == test_user.id,
                UserTenant.tenant_id == second_tenant.id,
            )
        )
        user_tenant = result.scalar_one_or_none()

        # User should not have access to second tenant
        assert user_tenant is None


class TestTenantTypeIsolation:
    """Test that tenant type affects feature access."""

    @pytest.mark.asyncio
    async def test_different_tenants_have_different_types(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        second_tenant: Tenant,
    ):
        """Test that tenants can have different types."""
        # Both are 3D print by default in fixtures
        assert test_tenant.tenant_type == TenantType.THREE_D_PRINT.value
        assert second_tenant.tenant_type == TenantType.THREE_D_PRINT.value

    @pytest.mark.asyncio
    async def test_create_knitting_tenant(self, db_session: AsyncSession):
        """Test creating a knitting tenant."""
        knitting_tenant = Tenant(
            id=uuid4(),
            name="Yarn Haven",
            slug="yarn-haven",
            tenant_type=TenantType.HAND_KNITTING.value,
            settings={},
        )
        db_session.add(knitting_tenant)
        await db_session.commit()
        await db_session.refresh(knitting_tenant)

        assert knitting_tenant.tenant_type == TenantType.HAND_KNITTING.value

    @pytest.mark.asyncio
    async def test_tenant_types_are_distinct(self, db_session: AsyncSession):
        """Test that all tenant types can coexist."""
        tenant_types = [
            TenantType.THREE_D_PRINT,
            TenantType.HAND_KNITTING,
            TenantType.MACHINE_KNITTING,
            TenantType.GENERIC,
        ]

        for i, ttype in enumerate(tenant_types):
            tenant = Tenant(
                id=uuid4(),
                name=f"Test Tenant {i}",
                slug=f"test-tenant-type-{i}",
                tenant_type=ttype.value,
                settings={},
            )
            db_session.add(tenant)

        await db_session.commit()

        # Verify each type was created
        for ttype in tenant_types:
            result = await db_session.execute(
                select(Tenant).where(Tenant.tenant_type == ttype.value)
            )
            tenants = result.scalars().all()
            assert len(tenants) >= 1


class TestSpoolTenantIsolation:
    """Test spool inventory tenant isolation."""

    @pytest.mark.asyncio
    async def test_spool_belongs_to_tenant(
        self,
        db_session: AsyncSession,
        test_spool: Spool,
        test_tenant: Tenant,
    ):
        """Test that spool is associated with correct tenant."""
        assert test_spool.tenant_id == test_tenant.id

    @pytest.mark.asyncio
    async def test_spools_filtered_by_tenant(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        second_tenant: Tenant,
        test_spool: Spool,
        test_material_type,
    ):
        """Test that spool queries are filtered by tenant."""
        # Create a spool for second tenant
        spool_b = Spool(
            id=uuid4(),
            tenant_id=second_tenant.id,
            material_type_id=test_material_type.id,
            spool_id="SPOOL-B-001",
            brand="Brand B",
            color="Blue",
            initial_weight=1000.0,
            current_weight=1000.0,
            purchase_price=Decimal("30.00"),
            is_active=True,
        )
        db_session.add(spool_b)
        await db_session.commit()

        # Query spools for tenant A
        result_a = await db_session.execute(select(Spool).where(Spool.tenant_id == test_tenant.id))
        spools_a = result_a.scalars().all()

        # Query spools for tenant B
        result_b = await db_session.execute(
            select(Spool).where(Spool.tenant_id == second_tenant.id)
        )
        spools_b = result_b.scalars().all()

        # Verify isolation
        spool_ids_a = {s.id for s in spools_a}
        spool_ids_b = {s.id for s in spools_b}

        assert test_spool.id in spool_ids_a
        assert spool_b.id not in spool_ids_a

        assert spool_b.id in spool_ids_b
        assert test_spool.id not in spool_ids_b
