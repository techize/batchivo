"""Tests for tenant member management API endpoints."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.user import User, UserRole, UserTenant


class TestTenantMemberEndpoints:
    """Tests for tenant member management API endpoints."""

    @pytest_asyncio.fixture
    async def owner_user(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> User:
        """Create an owner user for the tenant."""
        from app.auth.password import get_password_hash

        user = User(
            id=uuid4(),
            email="owner@example.com",
            full_name="Tenant Owner",
            hashed_password=get_password_hash("ownerpassword123"),
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        user_tenant = UserTenant(
            user_id=user.id,
            tenant_id=test_tenant.id,
            role=UserRole.OWNER,
        )
        db_session.add(user_tenant)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def admin_user(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> User:
        """Create an admin user for the tenant."""
        from app.auth.password import get_password_hash

        user = User(
            id=uuid4(),
            email="admin@example.com",
            full_name="Tenant Admin",
            hashed_password=get_password_hash("adminpassword123"),
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        user_tenant = UserTenant(
            user_id=user.id,
            tenant_id=test_tenant.id,
            role=UserRole.ADMIN,
        )
        db_session.add(user_tenant)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def member_user(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
    ) -> User:
        """Create a regular member user for the tenant."""
        from app.auth.password import get_password_hash

        user = User(
            id=uuid4(),
            email="member@example.com",
            full_name="Tenant Member",
            hashed_password=get_password_hash("memberpassword123"),
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        user_tenant = UserTenant(
            user_id=user.id,
            tenant_id=test_tenant.id,
            role=UserRole.MEMBER,
        )
        db_session.add(user_tenant)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def unaffiliated_user(
        self,
        db_session: AsyncSession,
    ) -> User:
        """Create a user not affiliated with the test tenant."""
        from app.auth.password import get_password_hash

        user = User(
            id=uuid4(),
            email="unaffiliated@example.com",
            full_name="Unaffiliated User",
            hashed_password=get_password_hash("unaffiliatedpassword123"),
            is_active=True,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def owner_client(
        self,
        db_session: AsyncSession,
        seed_material_types,
        owner_user: User,
        test_tenant: Tenant,
    ):
        """Create a test HTTP client authenticated as tenant owner."""
        from app.auth.dependencies import get_current_user, get_current_tenant
        from app.database import get_db
        from app.main import app

        # Load user_tenants relationship
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await db_session.execute(
            select(User).where(User.id == owner_user.id).options(selectinload(User.user_tenants))
        )
        owner_user = result.scalar_one()

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return owner_user

        async def override_get_current_tenant():
            return test_tenant

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_tenant] = override_get_current_tenant

        app.state.limiter.enabled = False

        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

        app.state.limiter.enabled = True
        app.dependency_overrides.clear()

    @pytest_asyncio.fixture
    async def admin_client(
        self,
        db_session: AsyncSession,
        seed_material_types,
        admin_user: User,
        test_tenant: Tenant,
    ):
        """Create a test HTTP client authenticated as tenant admin."""
        from app.auth.dependencies import get_current_user, get_current_tenant
        from app.database import get_db
        from app.main import app

        # Load user_tenants relationship
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await db_session.execute(
            select(User).where(User.id == admin_user.id).options(selectinload(User.user_tenants))
        )
        admin_user = result.scalar_one()

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return admin_user

        async def override_get_current_tenant():
            return test_tenant

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_tenant] = override_get_current_tenant

        app.state.limiter.enabled = False

        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

        app.state.limiter.enabled = True
        app.dependency_overrides.clear()

    @pytest_asyncio.fixture
    async def member_client(
        self,
        db_session: AsyncSession,
        seed_material_types,
        member_user: User,
        test_tenant: Tenant,
    ):
        """Create a test HTTP client authenticated as regular member."""
        from app.auth.dependencies import get_current_user, get_current_tenant
        from app.database import get_db
        from app.main import app

        # Load user_tenants relationship
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await db_session.execute(
            select(User).where(User.id == member_user.id).options(selectinload(User.user_tenants))
        )
        member_user = result.scalar_one()

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return member_user

        async def override_get_current_tenant():
            return test_tenant

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_tenant] = override_get_current_tenant

        app.state.limiter.enabled = False

        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

        app.state.limiter.enabled = True
        app.dependency_overrides.clear()

    # =========================================================================
    # List Members Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_list_members(
        self,
        owner_client: AsyncClient,
        owner_user: User,
    ):
        """Test listing tenant members."""
        response = await owner_client.get("/api/v1/tenant/members")

        assert response.status_code == 200
        data = response.json()
        assert "members" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_members_as_admin(
        self,
        admin_client: AsyncClient,
    ):
        """Test that admins can list members."""
        response = await admin_client.get("/api/v1/tenant/members")

        assert response.status_code == 200
        data = response.json()
        assert "members" in data

    @pytest.mark.asyncio
    async def test_list_members_as_member(
        self,
        member_client: AsyncClient,
    ):
        """Test that regular members can list members."""
        response = await member_client.get("/api/v1/tenant/members")

        assert response.status_code == 200
        data = response.json()
        assert "members" in data

    @pytest.mark.asyncio
    async def test_list_members_shows_all_details(
        self,
        owner_client: AsyncClient,
        owner_user: User,
    ):
        """Test that member list includes all expected fields."""
        response = await owner_client.get("/api/v1/tenant/members")

        assert response.status_code == 200
        data = response.json()

        for member in data["members"]:
            assert "id" in member
            assert "email" in member
            assert "full_name" in member
            assert "role" in member
            assert "is_active" in member
            assert "joined_at" in member

    # =========================================================================
    # Invite Member Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_invite_existing_user(
        self,
        owner_client: AsyncClient,
        unaffiliated_user: User,
    ):
        """Test inviting an existing user to the tenant."""
        response = await owner_client.post(
            "/api/v1/tenant/members/invite",
            json={"email": unaffiliated_user.email, "role": "member"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == unaffiliated_user.email
        assert data["role"] == "member"

    @pytest.mark.asyncio
    async def test_invite_nonexistent_user(
        self,
        owner_client: AsyncClient,
    ):
        """Test inviting a nonexistent user."""
        response = await owner_client.post(
            "/api/v1/tenant/members/invite",
            json={"email": "nonexistent@example.com", "role": "member"},
        )

        assert response.status_code == 404
        assert "register first" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invite_already_member(
        self,
        owner_client: AsyncClient,
        member_user: User,
    ):
        """Test inviting a user who is already a member."""
        response = await owner_client.post(
            "/api/v1/tenant/members/invite",
            json={"email": member_user.email, "role": "admin"},
        )

        assert response.status_code == 400
        assert "already a member" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invite_as_admin(
        self,
        admin_client: AsyncClient,
        unaffiliated_user: User,
    ):
        """Test that admins can invite users."""
        response = await admin_client.post(
            "/api/v1/tenant/members/invite",
            json={"email": unaffiliated_user.email, "role": "member"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_invite_as_member_forbidden(
        self,
        member_client: AsyncClient,
        unaffiliated_user: User,
    ):
        """Test that regular members cannot invite users."""
        response = await member_client.post(
            "/api/v1/tenant/members/invite",
            json={"email": unaffiliated_user.email, "role": "member"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_invite_as_owner(
        self,
        admin_client: AsyncClient,
        unaffiliated_user: User,
    ):
        """Test that admins cannot assign owner role."""
        response = await admin_client.post(
            "/api/v1/tenant/members/invite",
            json={"email": unaffiliated_user.email, "role": "owner"},
        )

        assert response.status_code == 403
        assert "owner" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_owner_can_invite_as_owner(
        self,
        owner_client: AsyncClient,
        unaffiliated_user: User,
    ):
        """Test that owners can assign owner role."""
        response = await owner_client.post(
            "/api/v1/tenant/members/invite",
            json={"email": unaffiliated_user.email, "role": "owner"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "owner"

    # =========================================================================
    # Update Member Role Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_update_member_role(
        self,
        owner_client: AsyncClient,
        member_user: User,
    ):
        """Test updating a member's role."""
        response = await owner_client.put(
            f"/api/v1/tenant/members/{member_user.id}",
            json={"role": "admin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"

    @pytest.mark.asyncio
    async def test_update_member_role_not_found(
        self,
        owner_client: AsyncClient,
    ):
        """Test updating a nonexistent member."""
        fake_id = uuid4()
        response = await owner_client.put(
            f"/api/v1/tenant/members/{fake_id}",
            json={"role": "admin"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_role_as_admin(
        self,
        admin_client: AsyncClient,
        member_user: User,
    ):
        """Test that admins can update member roles."""
        response = await admin_client.put(
            f"/api/v1/tenant/members/{member_user.id}",
            json={"role": "admin"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_role_as_member_forbidden(
        self,
        member_client: AsyncClient,
        admin_user: User,
    ):
        """Test that regular members cannot update roles."""
        response = await member_client.put(
            f"/api/v1/tenant/members/{admin_user.id}",
            json={"role": "member"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_promote_to_owner(
        self,
        admin_client: AsyncClient,
        member_user: User,
    ):
        """Test that admins cannot promote to owner."""
        response = await admin_client.put(
            f"/api/v1/tenant/members/{member_user.id}",
            json={"role": "owner"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_demote_owner(
        self,
        admin_client: AsyncClient,
        owner_user: User,
    ):
        """Test that admins cannot demote owners."""
        response = await admin_client.put(
            f"/api/v1/tenant/members/{owner_user.id}",
            json={"role": "admin"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_owner_cannot_demote_self(
        self,
        owner_client: AsyncClient,
        owner_user: User,
    ):
        """Test that owners cannot demote themselves."""
        response = await owner_client.put(
            f"/api/v1/tenant/members/{owner_user.id}",
            json={"role": "admin"},
        )

        assert response.status_code == 400
        assert "demote themselves" in response.json()["detail"].lower()

    # =========================================================================
    # Remove Member Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_remove_member(
        self,
        owner_client: AsyncClient,
        member_user: User,
    ):
        """Test removing a member from the tenant."""
        response = await owner_client.delete(f"/api/v1/tenant/members/{member_user.id}")

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_remove_member_not_found(
        self,
        owner_client: AsyncClient,
    ):
        """Test removing a nonexistent member."""
        fake_id = uuid4()
        response = await owner_client.delete(f"/api/v1/tenant/members/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_member_as_admin(
        self,
        admin_client: AsyncClient,
        member_user: User,
    ):
        """Test that admins can remove members."""
        response = await admin_client.delete(f"/api/v1/tenant/members/{member_user.id}")

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_remove_member_as_member_forbidden(
        self,
        member_client: AsyncClient,
        admin_user: User,
    ):
        """Test that regular members cannot remove others."""
        response = await member_client.delete(f"/api/v1/tenant/members/{admin_user.id}")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_remove_self(
        self,
        owner_client: AsyncClient,
        owner_user: User,
    ):
        """Test that users cannot remove themselves."""
        response = await owner_client.delete(f"/api/v1/tenant/members/{owner_user.id}")

        assert response.status_code == 400
        assert "remove yourself" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_admin_cannot_remove_owner(
        self,
        admin_client: AsyncClient,
        owner_user: User,
    ):
        """Test that admins cannot remove owners."""
        response = await admin_client.delete(f"/api/v1/tenant/members/{owner_user.id}")

        assert response.status_code == 403
