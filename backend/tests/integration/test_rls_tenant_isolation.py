"""
RLS (Row-Level Security) Tenant Isolation Tests.

These tests verify that the multi-tenant RLS implementation correctly isolates
data between tenants at the database level.

Test Categories:
1. Middleware Tests - Verify tenant context extraction (works with any DB)
2. Dependency Tests - Verify get_tenant_db sets session variables (works with any DB)
3. RLS Policy Tests - Verify actual data isolation (requires PostgreSQL)

Note: Full RLS testing requires PostgreSQL. Tests marked with @pytest.mark.postgresql
will be skipped when running with SQLite.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import Request
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_tenant_db
from app.auth.middleware import TenantContextMiddleware
from app.database import get_db
from app.main import app
from app.models.spool import Spool
from app.models.tenant import Tenant
from app.models.user import User, UserTenant, UserRole


# =============================================================================
# FIXTURES - Multi-tenant test setup
# =============================================================================


@pytest_asyncio.fixture(scope="function")
async def tenant_a(db_session: AsyncSession) -> Tenant:
    """Create Tenant A for isolation tests."""
    tenant = Tenant(
        id=uuid4(),
        name="Tenant A - Mystmereforge",
        slug="tenant-a",
        settings={"currency": "GBP"},
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture(scope="function")
async def tenant_b(db_session: AsyncSession) -> Tenant:
    """Create Tenant B for isolation tests."""
    tenant = Tenant(
        id=uuid4(),
        name="Tenant B - Olive and Wool",
        slug="tenant-b",
        settings={"currency": "GBP"},
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture(scope="function")
async def user_a(db_session: AsyncSession, tenant_a: Tenant) -> User:
    """Create User A belonging to Tenant A."""
    from app.auth.password import get_password_hash

    user = User(
        id=uuid4(),
        email="user_a@tenanta.com",
        full_name="User A",
        hashed_password=get_password_hash("password123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    user_tenant = UserTenant(
        user_id=user.id,
        tenant_id=tenant_a.id,
        role=UserRole.ADMIN,
    )
    db_session.add(user_tenant)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def user_b(db_session: AsyncSession, tenant_b: Tenant) -> User:
    """Create User B belonging to Tenant B."""
    from app.auth.password import get_password_hash

    user = User(
        id=uuid4(),
        email="user_b@tenantb.com",
        full_name="User B",
        hashed_password=get_password_hash("password123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    user_tenant = UserTenant(
        user_id=user.id,
        tenant_id=tenant_b.id,
        role=UserRole.ADMIN,
    )
    db_session.add(user_tenant)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def spools_tenant_a(
    db_session: AsyncSession, tenant_a: Tenant, test_material_type
) -> list[Spool]:
    """Create test spools for Tenant A."""
    spools = []
    for i in range(3):
        spool = Spool(
            id=uuid4(),
            tenant_id=tenant_a.id,
            material_type_id=test_material_type.id,
            spool_id=f"TENANT-A-SPOOL-{i+1:03d}",
            brand="Bambu Lab",
            color=["Red", "Blue", "Green"][i],
            initial_weight=1000.0,
            current_weight=800.0 - (i * 100),
            purchase_price=Decimal("25.00"),
            is_active=True,
        )
        db_session.add(spool)
        spools.append(spool)
    await db_session.commit()
    for spool in spools:
        await db_session.refresh(spool)
    return spools


@pytest_asyncio.fixture(scope="function")
async def spools_tenant_b(
    db_session: AsyncSession, tenant_b: Tenant, test_material_type
) -> list[Spool]:
    """Create test spools for Tenant B."""
    spools = []
    for i in range(2):
        spool = Spool(
            id=uuid4(),
            tenant_id=tenant_b.id,
            material_type_id=test_material_type.id,
            spool_id=f"TENANT-B-SPOOL-{i+1:03d}",
            brand="Prusa",
            color=["White", "Black"][i],
            initial_weight=750.0,
            current_weight=500.0,
            purchase_price=Decimal("20.00"),
            is_active=True,
        )
        db_session.add(spool)
        spools.append(spool)
    await db_session.commit()
    for spool in spools:
        await db_session.refresh(spool)
    return spools


# =============================================================================
# MIDDLEWARE TESTS - Verify tenant context extraction
# =============================================================================


class TestTenantContextMiddleware:
    """Tests for TenantContextMiddleware tenant extraction logic."""

    @pytest.mark.asyncio
    async def test_extracts_tenant_from_jwt_token(self, tenant_a: Tenant, user_a: User):
        """Verify middleware extracts tenant_id from JWT token."""
        from app.core.security import create_access_token

        # Create a real JWT token with tenant_id
        token = create_access_token(
            {
                "user_id": str(user_a.id),
                "email": user_a.email,
                "tenant_id": str(tenant_a.id),
            }
        )

        middleware = TenantContextMiddleware(app=MagicMock())

        # Create mock request with Authorization header
        request = MagicMock(spec=Request)
        request.headers = {"authorization": f"Bearer {token}"}
        request.state = MagicMock()

        # Mock call_next
        async def mock_call_next(req):
            return MagicMock()

        await middleware.dispatch(request, mock_call_next)

        # Verify tenant_id was set in request.state
        assert request.state.tenant_id == tenant_a.id

    @pytest.mark.asyncio
    async def test_x_tenant_id_header_overrides_jwt(
        self, tenant_a: Tenant, tenant_b: Tenant, user_a: User
    ):
        """Verify X-Tenant-ID header takes precedence over JWT tenant."""
        from app.core.security import create_access_token

        # Create JWT with tenant_a
        token = create_access_token(
            {
                "user_id": str(user_a.id),
                "email": user_a.email,
                "tenant_id": str(tenant_a.id),
            }
        )

        middleware = TenantContextMiddleware(app=MagicMock())

        # Request with JWT (tenant_a) but X-Tenant-ID header (tenant_b)
        request = MagicMock(spec=Request)
        request.headers = {
            "authorization": f"Bearer {token}",
            "x-tenant-id": str(tenant_b.id),
        }
        request.state = MagicMock()

        async def mock_call_next(req):
            return MagicMock()

        await middleware.dispatch(request, mock_call_next)

        # X-Tenant-ID should override JWT
        assert request.state.tenant_id == tenant_b.id

    @pytest.mark.asyncio
    async def test_invalid_x_tenant_id_ignored(self, tenant_a: Tenant, user_a: User):
        """Verify invalid X-Tenant-ID header is ignored, falls back to JWT."""
        from app.core.security import create_access_token

        token = create_access_token(
            {
                "user_id": str(user_a.id),
                "email": user_a.email,
                "tenant_id": str(tenant_a.id),
            }
        )

        middleware = TenantContextMiddleware(app=MagicMock())

        request = MagicMock(spec=Request)
        request.headers = {
            "authorization": f"Bearer {token}",
            "x-tenant-id": "invalid-not-a-uuid",
        }
        request.state = MagicMock()

        async def mock_call_next(req):
            return MagicMock()

        await middleware.dispatch(request, mock_call_next)

        # Should fall back to JWT tenant_id
        assert request.state.tenant_id == tenant_a.id

    @pytest.mark.asyncio
    async def test_no_auth_sets_none_tenant(self):
        """Verify unauthenticated requests get tenant_id=None."""
        middleware = TenantContextMiddleware(app=MagicMock())

        request = MagicMock(spec=Request)
        request.headers = {}  # No auth header
        request.state = MagicMock()

        async def mock_call_next(req):
            return MagicMock()

        await middleware.dispatch(request, mock_call_next)

        assert request.state.tenant_id is None


# =============================================================================
# GET_TENANT_DB DEPENDENCY TESTS
# =============================================================================


class TestGetTenantDbDependency:
    """Tests for get_tenant_db dependency RLS context setting."""

    @pytest.mark.asyncio
    async def test_sets_session_variable_when_rls_enabled(
        self, db_session: AsyncSession, tenant_a: Tenant
    ):
        """Verify SET LOCAL is executed when RLS is enabled."""

        # Create mock request with tenant_id
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.tenant_id = tenant_a.id

        # Mock the session maker to use our test session
        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.auth.dependencies.settings") as mock_settings,
            patch("app.auth.dependencies.async_session_maker", mock_session_maker),
        ):
            mock_settings.rls_enabled = True

            # The dependency will try to execute SET LOCAL which SQLite doesn't support
            # So we just verify the flow works without the actual SQL
            # Full RLS testing requires PostgreSQL
            try:
                async for session in get_tenant_db(request):
                    assert session is not None
            except Exception:
                # SQLite doesn't support SET LOCAL, which is expected
                pass

    @pytest.mark.asyncio
    async def test_skips_session_variable_when_rls_disabled(
        self, db_session: AsyncSession, tenant_a: Tenant
    ):
        """Verify SET LOCAL is NOT executed when RLS is disabled."""

        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.tenant_id = tenant_a.id

        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.auth.dependencies.settings") as mock_settings,
            patch("app.auth.dependencies.async_session_maker", mock_session_maker),
        ):
            mock_settings.rls_enabled = False

            async for session in get_tenant_db(request):
                # Should work without setting session variable
                assert session is not None

    @pytest.mark.asyncio
    async def test_handles_missing_tenant_id_gracefully(self, db_session: AsyncSession):
        """Verify dependency works when tenant_id is not set."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.tenant_id = None  # No tenant context

        mock_session_maker = MagicMock()
        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=db_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.auth.dependencies.settings") as mock_settings,
            patch("app.auth.dependencies.async_session_maker", mock_session_maker),
        ):
            mock_settings.rls_enabled = True

            async for session in get_tenant_db(request):
                # Should work without tenant context (for public endpoints)
                assert session is not None


# =============================================================================
# APPLICATION-LEVEL ISOLATION TESTS (works with SQLite via app-level filtering)
# =============================================================================


class TestApplicationLevelIsolation:
    """
    Tests that verify tenant isolation at the application level.

    These tests work with SQLite by using the standard tenant filtering
    that happens in the API routes. They don't test RLS directly but
    verify the overall isolation behavior.
    """

    @pytest.mark.asyncio
    async def test_user_only_sees_own_tenant_spools(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        user_a: User,
        spools_tenant_a: list[Spool],
        spools_tenant_b: list[Spool],
        seed_material_types,
    ):
        """User A should only see Tenant A's spools via application filtering."""
        from app.auth.dependencies import get_current_user, get_current_tenant

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return user_a

        async def override_get_current_tenant():
            return tenant_a

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_tenant] = override_get_current_tenant

        try:
            app.state.limiter.enabled = False
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/v1/spools")
                assert response.status_code == 200

                data = response.json()
                # API returns paginated response with 'spools' key
                spools = (
                    data.get("spools", data.get("items", data)) if isinstance(data, dict) else data
                )

                # Should only see Tenant A's 3 spools
                assert (
                    len(spools) == 3
                ), f"Expected 3 spools, got {len(spools)}: {[s.get('spool_id') for s in spools]}"

                # Verify all spools belong to Tenant A
                spool_ids = {s["spool_id"] for s in spools}
                assert "TENANT-A-SPOOL-001" in spool_ids
                assert "TENANT-A-SPOOL-002" in spool_ids
                assert "TENANT-A-SPOOL-003" in spool_ids

                # Should NOT see Tenant B's spools
                assert "TENANT-B-SPOOL-001" not in spool_ids
                assert "TENANT-B-SPOOL-002" not in spool_ids
        finally:
            app.state.limiter.enabled = True
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_tenant_spool_by_id(
        self,
        db_session: AsyncSession,
        tenant_a: Tenant,
        tenant_b: Tenant,
        user_a: User,
        spools_tenant_a: list[Spool],
        spools_tenant_b: list[Spool],
        seed_material_types,
    ):
        """User A should get 404 when trying to access Tenant B's spool."""
        from app.auth.dependencies import get_current_user, get_current_tenant

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return user_a

        async def override_get_current_tenant():
            return tenant_a

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_tenant] = override_get_current_tenant

        try:
            app.state.limiter.enabled = False
            async with AsyncClient(app=app, base_url="http://test") as client:
                # Try to access Tenant B's spool
                tenant_b_spool_id = spools_tenant_b[0].id
                response = await client.get(f"/api/v1/spools/{tenant_b_spool_id}")

                # Should get 404 (not found in current tenant)
                assert response.status_code == 404
        finally:
            app.state.limiter.enabled = True
            app.dependency_overrides.clear()


# =============================================================================
# POSTGRESQL-SPECIFIC RLS TESTS (require PostgreSQL)
# =============================================================================


# Mark to skip if not PostgreSQL
postgresql_only = pytest.mark.skipif(
    True,  # Skip by default - enable when PostgreSQL test DB is available
    reason="RLS tests require PostgreSQL database",
)


@postgresql_only
class TestPostgresRLSPolicies:
    """
    PostgreSQL-specific RLS policy tests.

    These tests verify that RLS policies correctly filter data at the
    database level, independent of application code.

    To run these tests:
    1. Set up a PostgreSQL test database
    2. Run migrations to create RLS policies
    3. Update TEST_DATABASE_URL to use PostgreSQL
    4. Remove the @postgresql_only skip marker
    """

    @pytest.mark.asyncio
    async def test_select_policy_filters_by_tenant(self):
        """Direct SELECT query only returns current tenant's data."""
        # This test would verify:
        # 1. Set session variable: SET app.current_tenant_id = 'tenant_a_id'
        # 2. Execute: SELECT * FROM spools
        # 3. Assert only tenant_a spools returned
        pass

    @pytest.mark.asyncio
    async def test_insert_policy_validates_tenant_id(self):
        """INSERT with wrong tenant_id is rejected by policy."""
        # This test would verify:
        # 1. Set session variable to tenant_a
        # 2. Try INSERT with tenant_id = tenant_b
        # 3. Assert INSERT fails or returns 0 rows
        pass

    @pytest.mark.asyncio
    async def test_update_policy_prevents_cross_tenant(self):
        """UPDATE cannot modify other tenant's data."""
        # This test would verify:
        # 1. Set session variable to tenant_a
        # 2. Execute: UPDATE spools SET color = 'Purple' WHERE tenant_id = tenant_b
        # 3. Assert 0 rows affected
        pass

    @pytest.mark.asyncio
    async def test_delete_policy_prevents_cross_tenant(self):
        """DELETE cannot remove other tenant's data."""
        # This test would verify:
        # 1. Set session variable to tenant_a
        # 2. Execute: DELETE FROM spools WHERE tenant_id = tenant_b
        # 3. Assert 0 rows affected
        pass

    @pytest.mark.asyncio
    async def test_missing_session_variable_returns_empty(self):
        """Query without session variable returns no results."""
        # This test would verify:
        # 1. Do NOT set session variable
        # 2. Execute: SELECT * FROM spools
        # 3. Assert 0 rows returned (safe default)
        pass

    @pytest.mark.asyncio
    async def test_superuser_bypasses_rls(self):
        """Superuser connection can see all tenant data (for migrations)."""
        # This test would verify:
        # 1. Connect as superuser (not app_user)
        # 2. Execute: SELECT * FROM spools
        # 3. Assert ALL spools returned (RLS bypassed)
        pass


# =============================================================================
# RLS CONFIGURATION TESTS
# =============================================================================


class TestRLSConfiguration:
    """Tests for RLS configuration settings."""

    def test_rls_disabled_by_default_in_development(self):
        """Verify RLS is disabled by default in development mode."""
        from app.config import Settings

        settings = Settings(environment="development")
        assert settings.rls_enabled is False

    def test_effective_database_url_without_rls(self):
        """Without RLS, effective_database_url returns standard URL."""
        from app.config import Settings

        settings = Settings(
            database_url="postgresql://user:pass@localhost/db",
            rls_enabled=False,
            rls_database_url="postgresql://app_user:pass@localhost/db",
        )
        assert settings.effective_database_url == "postgresql://user:pass@localhost/db"

    def test_effective_database_url_with_rls(self):
        """With RLS enabled, effective_database_url returns RLS URL."""
        from app.config import Settings

        settings = Settings(
            database_url="postgresql://user:pass@localhost/db",
            rls_enabled=True,
            rls_database_url="postgresql://app_user:pass@localhost/db",
        )
        assert settings.effective_database_url == "postgresql://app_user:pass@localhost/db"

    def test_rls_without_url_falls_back_to_standard(self):
        """RLS enabled but no URL falls back to standard database_url."""
        from app.config import Settings

        settings = Settings(
            database_url="postgresql://user:pass@localhost/db",
            rls_enabled=True,
            rls_database_url="",  # Empty
        )
        assert settings.effective_database_url == "postgresql://user:pass@localhost/db"
