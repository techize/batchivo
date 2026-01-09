"""Full-text search service for products.

Provides PostgreSQL full-text search with weighted fields and SQLite fallback for testing.
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.product import Product


class SearchService:
    """
    Service for full-text search on products.

    Uses PostgreSQL tsvector/tsquery for production and falls back to LIKE
    for SQLite during testing.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _is_postgres(self) -> bool:
        """Check if we're using PostgreSQL (supports FTS) or SQLite (fallback)."""
        try:
            result = await self.db.execute(text("SELECT version()"))
            version = result.scalar()
            return version is not None and "PostgreSQL" in str(version)
        except Exception:
            return False

    async def search_products(
        self,
        query: str,
        tenant_id: Optional[UUID] = None,
        shop_visible_only: bool = False,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Product], int]:
        """
        Search products using full-text search.

        Args:
            query: Search query string
            tenant_id: Optional tenant filter (for admin search)
            shop_visible_only: If True, only return shop-visible products
            active_only: If True, only return active products
            limit: Maximum results to return
            offset: Offset for pagination

        Returns:
            Tuple of (products, total_count)
        """
        if not query or not query.strip():
            return [], 0

        is_postgres = await self._is_postgres()

        if is_postgres:
            return await self._search_postgres(
                query=query,
                tenant_id=tenant_id,
                shop_visible_only=shop_visible_only,
                active_only=active_only,
                limit=limit,
                offset=offset,
            )
        else:
            return await self._search_fallback(
                query=query,
                tenant_id=tenant_id,
                shop_visible_only=shop_visible_only,
                active_only=active_only,
                limit=limit,
                offset=offset,
            )

    async def _search_postgres(
        self,
        query: str,
        tenant_id: Optional[UUID],
        shop_visible_only: bool,
        active_only: bool,
        limit: int,
        offset: int,
    ) -> tuple[list[Product], int]:
        """
        Search using PostgreSQL full-text search with ts_rank for relevance.

        Uses plainto_tsquery for natural language query parsing.
        """
        # Clean and prepare query
        search_query = query.strip()

        # Build the tsquery - use plainto_tsquery for natural language
        # This handles phrases and common words automatically
        tsquery = func.plainto_tsquery("english", search_query)

        # Build base query with relevance ranking
        base_query = select(Product).where(Product.search_vector.op("@@")(tsquery))

        # Apply filters
        if tenant_id:
            base_query = base_query.where(Product.tenant_id == tenant_id)

        if shop_visible_only:
            base_query = base_query.where(Product.shop_visible.is_(True))

        if active_only:
            base_query = base_query.where(Product.is_active.is_(True))

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Add relevance ranking and pagination
        # ts_rank scores how well the document matches the query
        rank = func.ts_rank(Product.search_vector, tsquery)
        results_query = (
            base_query.add_columns(rank.label("rank"))
            .order_by(rank.desc(), Product.name)
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(results_query)
        # Extract just the Product objects (first element of each row)
        products = [row[0] for row in result.all()]

        return products, total

    async def _search_fallback(
        self,
        query: str,
        tenant_id: Optional[UUID],
        shop_visible_only: bool,
        active_only: bool,
        limit: int,
        offset: int,
    ) -> tuple[list[Product], int]:
        """
        Fallback search using LIKE for SQLite (testing).

        Searches name, SKU, and description with case-insensitive matching.
        """
        search_pattern = f"%{query.strip()}%"

        # Build base query with LIKE search
        base_query = select(Product).where(
            or_(
                Product.name.ilike(search_pattern),
                Product.sku.ilike(search_pattern),
                Product.description.ilike(search_pattern),
            )
        )

        # Apply filters
        if tenant_id:
            base_query = base_query.where(Product.tenant_id == tenant_id)

        if shop_visible_only:
            base_query = base_query.where(Product.shop_visible.is_(True))

        if active_only:
            base_query = base_query.where(Product.is_active.is_(True))

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        results_query = base_query.order_by(Product.name).offset(offset).limit(limit)

        result = await self.db.execute(results_query)
        products = list(result.scalars().all())

        return products, total

    async def update_search_vector(self, product: Product) -> None:
        """
        Manually update a product's search vector.

        Note: In PostgreSQL, this is handled automatically by triggers.
        This method is provided for manual updates or testing.
        """
        is_postgres = await self._is_postgres()

        if is_postgres:
            # Update search vector using raw SQL
            await self.db.execute(
                text("""
                    UPDATE products
                    SET search_vector = (
                        setweight(to_tsvector('english', COALESCE(name, '')), 'A') ||
                        setweight(to_tsvector('english', COALESCE(sku, '')), 'B') ||
                        setweight(to_tsvector('english', COALESCE(description, '')), 'C') ||
                        setweight(to_tsvector('english', COALESCE(shop_description, '')), 'C')
                    )
                    WHERE id = :product_id
                """),
                {"product_id": str(product.id)},
            )
            await self.db.commit()

    async def rebuild_all_search_vectors(self, tenant_id: Optional[UUID] = None) -> int:
        """
        Rebuild search vectors for all products.

        Useful after migration or bulk imports.

        Args:
            tenant_id: Optional tenant to limit rebuild to

        Returns:
            Number of products updated
        """
        is_postgres = await self._is_postgres()

        if not is_postgres:
            return 0

        # Build the update query
        if tenant_id:
            result = await self.db.execute(
                text("""
                    UPDATE products
                    SET search_vector = (
                        setweight(to_tsvector('english', COALESCE(name, '')), 'A') ||
                        setweight(to_tsvector('english', COALESCE(sku, '')), 'B') ||
                        setweight(to_tsvector('english', COALESCE(description, '')), 'C') ||
                        setweight(to_tsvector('english', COALESCE(shop_description, '')), 'C')
                    )
                    WHERE tenant_id = :tenant_id
                """),
                {"tenant_id": str(tenant_id)},
            )
        else:
            result = await self.db.execute(
                text("""
                    UPDATE products
                    SET search_vector = (
                        setweight(to_tsvector('english', COALESCE(name, '')), 'A') ||
                        setweight(to_tsvector('english', COALESCE(sku, '')), 'B') ||
                        setweight(to_tsvector('english', COALESCE(description, '')), 'C') ||
                        setweight(to_tsvector('english', COALESCE(shop_description, '')), 'C')
                    )
                """)
            )

        await self.db.commit()
        return result.rowcount


async def get_search_service(
    db: AsyncSession = Depends(get_db),
) -> SearchService:
    """Dependency to get search service instance."""
    return SearchService(db)
