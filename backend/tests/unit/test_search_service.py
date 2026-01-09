"""Unit tests for the search service."""

import pytest

from app.services.search_service import SearchService


class TestSearchService:
    """Tests for SearchService."""

    @pytest.fixture
    async def search_service(self, db_session):
        """Create a search service instance."""
        return SearchService(db_session)

    async def test_search_empty_query_returns_empty(self, search_service, test_tenant):
        """Empty search query should return empty results."""
        products, total = await search_service.search_products(
            query="",
            tenant_id=test_tenant.id,
        )
        assert products == []
        assert total == 0

    async def test_search_whitespace_query_returns_empty(self, search_service, test_tenant):
        """Whitespace-only query should return empty results."""
        products, total = await search_service.search_products(
            query="   ",
            tenant_id=test_tenant.id,
        )
        assert products == []
        assert total == 0

    async def test_search_finds_product_by_name(self, search_service, db_session, test_tenant):
        """Search should find products by name."""
        from app.models.product import Product

        # Create a product with specific name
        product = Product(
            tenant_id=test_tenant.id,
            sku="SEARCH-TEST-001",
            name="Unique Dragon Figurine",
            description="A beautiful handcrafted dragon",
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()

        # Search for the product
        products, total = await search_service.search_products(
            query="Dragon Figurine",
            tenant_id=test_tenant.id,
        )

        assert total >= 1
        assert any(p.sku == "SEARCH-TEST-001" for p in products)

    async def test_search_finds_product_by_sku(self, search_service, db_session, test_tenant):
        """Search should find products by SKU."""
        from app.models.product import Product

        product = Product(
            tenant_id=test_tenant.id,
            sku="UNIQUE-SKU-XYZ123",
            name="Regular Product",
            description="A regular product",
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()

        products, total = await search_service.search_products(
            query="XYZ123",
            tenant_id=test_tenant.id,
        )

        assert total >= 1
        assert any(p.sku == "UNIQUE-SKU-XYZ123" for p in products)

    async def test_search_finds_product_by_description(
        self, search_service, db_session, test_tenant
    ):
        """Search should find products by description."""
        from app.models.product import Product

        product = Product(
            tenant_id=test_tenant.id,
            sku="DESC-SEARCH-001",
            name="Some Product",
            description="Contains the word archipelago in the description",
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()

        products, total = await search_service.search_products(
            query="archipelago",
            tenant_id=test_tenant.id,
        )

        assert total >= 1
        assert any(p.sku == "DESC-SEARCH-001" for p in products)

    async def test_search_respects_tenant_isolation(self, search_service, db_session, test_tenant):
        """Search should only return products from specified tenant."""
        from app.models.product import Product
        from app.models.tenant import Tenant

        # Create another tenant
        other_tenant = Tenant(
            name="Other Tenant",
            slug="other-tenant",
        )
        db_session.add(other_tenant)
        await db_session.flush()

        # Create products for both tenants with same searchable term
        product1 = Product(
            tenant_id=test_tenant.id,
            sku="TENANT1-SEARCH",
            name="Magic Widget Test Tenant",
            is_active=True,
        )
        product2 = Product(
            tenant_id=other_tenant.id,
            sku="TENANT2-SEARCH",
            name="Magic Widget Other Tenant",
            is_active=True,
        )
        db_session.add_all([product1, product2])
        await db_session.commit()

        # Search for test_tenant only
        products, total = await search_service.search_products(
            query="Magic Widget",
            tenant_id=test_tenant.id,
        )

        # Should find only test_tenant's product
        found_skus = [p.sku for p in products]
        assert "TENANT1-SEARCH" in found_skus
        assert "TENANT2-SEARCH" not in found_skus

    async def test_search_respects_active_filter(self, search_service, db_session, test_tenant):
        """Search should respect active_only filter."""
        from app.models.product import Product

        # Create active and inactive products
        active_product = Product(
            tenant_id=test_tenant.id,
            sku="ACTIVE-SEARCHABLE",
            name="Searchable Active Item",
            is_active=True,
        )
        inactive_product = Product(
            tenant_id=test_tenant.id,
            sku="INACTIVE-SEARCHABLE",
            name="Searchable Inactive Item",
            is_active=False,
        )
        db_session.add_all([active_product, inactive_product])
        await db_session.commit()

        # Search with active_only=True
        products, _ = await search_service.search_products(
            query="Searchable",
            tenant_id=test_tenant.id,
            active_only=True,
        )

        found_skus = [p.sku for p in products]
        assert "ACTIVE-SEARCHABLE" in found_skus
        assert "INACTIVE-SEARCHABLE" not in found_skus

        # Search with active_only=False
        products, _ = await search_service.search_products(
            query="Searchable",
            tenant_id=test_tenant.id,
            active_only=False,
        )

        found_skus = [p.sku for p in products]
        assert "ACTIVE-SEARCHABLE" in found_skus
        assert "INACTIVE-SEARCHABLE" in found_skus

    async def test_search_respects_shop_visible_filter(
        self, search_service, db_session, test_tenant
    ):
        """Search should respect shop_visible_only filter."""
        from app.models.product import Product

        visible_product = Product(
            tenant_id=test_tenant.id,
            sku="VISIBLE-SEARCH",
            name="Searchable Visible Item",
            is_active=True,
            shop_visible=True,
        )
        hidden_product = Product(
            tenant_id=test_tenant.id,
            sku="HIDDEN-SEARCH",
            name="Searchable Hidden Item",
            is_active=True,
            shop_visible=False,
        )
        db_session.add_all([visible_product, hidden_product])
        await db_session.commit()

        # Search with shop_visible_only=True
        products, _ = await search_service.search_products(
            query="Searchable",
            tenant_id=test_tenant.id,
            shop_visible_only=True,
        )

        found_skus = [p.sku for p in products]
        assert "VISIBLE-SEARCH" in found_skus
        assert "HIDDEN-SEARCH" not in found_skus

    async def test_search_pagination(self, search_service, db_session, test_tenant):
        """Search should support pagination."""
        from app.models.product import Product

        # Create multiple products
        for i in range(5):
            product = Product(
                tenant_id=test_tenant.id,
                sku=f"PAGINATE-SEARCH-{i}",
                name=f"Paginated Search Item {i}",
                is_active=True,
            )
            db_session.add(product)
        await db_session.commit()

        # Get first page
        products, total = await search_service.search_products(
            query="Paginated Search",
            tenant_id=test_tenant.id,
            limit=2,
            offset=0,
        )
        assert len(products) == 2
        assert total >= 5

        # Get second page
        products, total = await search_service.search_products(
            query="Paginated Search",
            tenant_id=test_tenant.id,
            limit=2,
            offset=2,
        )
        assert len(products) == 2

    async def test_search_case_insensitive(self, search_service, db_session, test_tenant):
        """Search should be case insensitive."""
        from app.models.product import Product

        product = Product(
            tenant_id=test_tenant.id,
            sku="CASE-INSENSITIVE",
            name="UPPERCASE NAME lowercase description",
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()

        # Search with different cases
        products_lower, _ = await search_service.search_products(
            query="uppercase",
            tenant_id=test_tenant.id,
        )
        products_upper, _ = await search_service.search_products(
            query="UPPERCASE",
            tenant_id=test_tenant.id,
        )
        products_mixed, _ = await search_service.search_products(
            query="UpperCase",
            tenant_id=test_tenant.id,
        )

        # All searches should find the product
        assert any(p.sku == "CASE-INSENSITIVE" for p in products_lower)
        assert any(p.sku == "CASE-INSENSITIVE" for p in products_upper)
        assert any(p.sku == "CASE-INSENSITIVE" for p in products_mixed)

    async def test_search_partial_match(self, search_service, db_session, test_tenant):
        """Search should find partial matches (prefix/suffix)."""
        from app.models.product import Product

        product = Product(
            tenant_id=test_tenant.id,
            sku="PARTIAL-MATCH-TEST",
            name="Mystmereforge Dragon",
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()

        # Search with partial term
        products, total = await search_service.search_products(
            query="Dragon",
            tenant_id=test_tenant.id,
        )

        assert any(p.sku == "PARTIAL-MATCH-TEST" for p in products)

    async def test_search_no_results(self, search_service, test_tenant):
        """Search should return empty when no matches found."""
        products, total = await search_service.search_products(
            query="xyznonexistentproduct123",
            tenant_id=test_tenant.id,
        )
        assert products == []
        assert total == 0
