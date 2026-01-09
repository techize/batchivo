"""Integration tests for pages API endpoints."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from uuid import uuid4

from app.models.page import Page, PageType
from app.models.tenant import Tenant


@pytest_asyncio.fixture
async def test_page(db_session, test_tenant: Tenant) -> Page:
    """Create a test page."""
    page = Page(
        id=uuid4(),
        tenant_id=test_tenant.id,
        slug="privacy-policy",
        title="Privacy Policy",
        content="# Privacy Policy\n\nThis is our privacy policy.",
        page_type=PageType.POLICY.value,
        meta_description="Our privacy policy for the shop",
        is_published=True,
        sort_order=0,
    )
    db_session.add(page)
    await db_session.commit()
    await db_session.refresh(page)
    return page


@pytest_asyncio.fixture
async def test_unpublished_page(db_session, test_tenant: Tenant) -> Page:
    """Create an unpublished test page."""
    page = Page(
        id=uuid4(),
        tenant_id=test_tenant.id,
        slug="draft-terms",
        title="Terms Draft",
        content="# Terms\n\nDraft content.",
        page_type=PageType.POLICY.value,
        is_published=False,
        sort_order=1,
    )
    db_session.add(page)
    await db_session.commit()
    await db_session.refresh(page)
    return page


class TestPageCRUD:
    """Test page CRUD API endpoints."""

    @pytest.mark.asyncio
    async def test_create_page(self, client: AsyncClient, auth_headers: dict):
        """Test page creation."""
        response = await client.post(
            "/api/v1/pages",
            headers=auth_headers,
            json={
                "title": "Returns Policy",
                "content": "# Returns\n\nYou can return items within 30 days.",
                "page_type": "policy",
                "is_published": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Returns Policy"
        assert data["slug"] == "returns-policy"
        assert data["page_type"] == "policy"
        assert data["is_published"] is True
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_page_auto_slug(self, client: AsyncClient, auth_headers: dict):
        """Test page creation auto-generates slug from title."""
        response = await client.post(
            "/api/v1/pages",
            headers=auth_headers,
            json={
                "title": "My Special Page!",
                "content": "Content here",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "my-special-page"

    @pytest.mark.asyncio
    async def test_create_page_custom_slug(self, client: AsyncClient, auth_headers: dict):
        """Test page creation with custom slug."""
        response = await client.post(
            "/api/v1/pages",
            headers=auth_headers,
            json={
                "title": "Custom Slug Page",
                "slug": "my-custom-slug",
                "content": "Content",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "my-custom-slug"

    @pytest.mark.asyncio
    async def test_create_page_duplicate_slug(
        self, client: AsyncClient, auth_headers: dict, test_page: Page
    ):
        """Test creating page with duplicate slug fails."""
        response = await client.post(
            "/api/v1/pages",
            headers=auth_headers,
            json={
                "title": "Another Page",
                "slug": test_page.slug,  # Duplicate
                "content": "Content",
            },
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_pages(self, client: AsyncClient, auth_headers: dict, test_page: Page):
        """Test listing pages."""
        response = await client.get("/api/v1/pages", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "pages" in data
        assert "total" in data
        assert len(data["pages"]) >= 1

    @pytest.mark.asyncio
    async def test_list_pages_includes_unpublished(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_page: Page,
        test_unpublished_page: Page,
    ):
        """Test listing pages includes unpublished by default (admin view)."""
        response = await client.get("/api/v1/pages", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        slugs = [p["slug"] for p in data["pages"]]
        assert test_page.slug in slugs
        assert test_unpublished_page.slug in slugs

    @pytest.mark.asyncio
    async def test_list_pages_filter_unpublished(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_page: Page,
        test_unpublished_page: Page,
    ):
        """Test filtering to only published pages."""
        response = await client.get("/api/v1/pages?include_unpublished=false", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        slugs = [p["slug"] for p in data["pages"]]
        assert test_page.slug in slugs
        assert test_unpublished_page.slug not in slugs

    @pytest.mark.asyncio
    async def test_list_pages_filter_by_type(
        self, client: AsyncClient, auth_headers: dict, test_page: Page
    ):
        """Test filtering pages by type."""
        response = await client.get("/api/v1/pages?page_type=policy", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert all(p["page_type"] == "policy" for p in data["pages"])

    @pytest.mark.asyncio
    async def test_list_pages_search(
        self, client: AsyncClient, auth_headers: dict, test_page: Page
    ):
        """Test searching pages by title."""
        response = await client.get(
            f"/api/v1/pages?search={test_page.title[:7]}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["pages"]) >= 1
        assert any(p["id"] == str(test_page.id) for p in data["pages"])

    @pytest.mark.asyncio
    async def test_get_page(self, client: AsyncClient, auth_headers: dict, test_page: Page):
        """Test getting a single page."""
        response = await client.get(f"/api/v1/pages/{test_page.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_page.id)
        assert data["title"] == test_page.title
        assert data["slug"] == test_page.slug
        assert data["content"] == test_page.content

    @pytest.mark.asyncio
    async def test_get_page_not_found(self, client: AsyncClient, auth_headers: dict):
        """Test getting non-existent page returns 404."""
        fake_id = uuid4()
        response = await client.get(f"/api/v1/pages/{fake_id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_page(self, client: AsyncClient, auth_headers: dict, test_page: Page):
        """Test updating a page."""
        response = await client.patch(
            f"/api/v1/pages/{test_page.id}",
            headers=auth_headers,
            json={
                "title": "Updated Privacy Policy",
                "content": "# Updated Privacy Policy\n\nNew content here.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Privacy Policy"
        assert "Updated Privacy Policy" in data["content"]

    @pytest.mark.asyncio
    async def test_update_page_slug(self, client: AsyncClient, auth_headers: dict, test_page: Page):
        """Test updating page slug."""
        response = await client.patch(
            f"/api/v1/pages/{test_page.id}",
            headers=auth_headers,
            json={"slug": "updated-privacy"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "updated-privacy"

    @pytest.mark.asyncio
    async def test_update_page_duplicate_slug_fails(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_page: Page,
        db_session,
        test_tenant: Tenant,
    ):
        """Test updating page to duplicate slug fails."""
        # Create another page
        other_page = Page(
            id=uuid4(),
            tenant_id=test_tenant.id,
            slug="other-page",
            title="Other Page",
            content="Other content",
            page_type=PageType.POLICY.value,
            is_published=True,
        )
        db_session.add(other_page)
        await db_session.commit()

        # Try to update test_page to use other_page's slug
        response = await client.patch(
            f"/api/v1/pages/{test_page.id}",
            headers=auth_headers,
            json={"slug": "other-page"},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_update_page_publish(
        self, client: AsyncClient, auth_headers: dict, test_unpublished_page: Page
    ):
        """Test publishing a page."""
        response = await client.patch(
            f"/api/v1/pages/{test_unpublished_page.id}",
            headers=auth_headers,
            json={"is_published": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_published"] is True

    @pytest.mark.asyncio
    async def test_delete_page_soft(self, client: AsyncClient, auth_headers: dict, test_page: Page):
        """Test soft deleting (unpublishing) a page."""
        response = await client.delete(f"/api/v1/pages/{test_page.id}", headers=auth_headers)
        assert response.status_code == 204

        # Page should still exist but be unpublished
        response = await client.get(f"/api/v1/pages/{test_page.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["is_published"] is False

    @pytest.mark.asyncio
    async def test_delete_page_hard(self, client: AsyncClient, auth_headers: dict, test_page: Page):
        """Test hard deleting a page."""
        response = await client.delete(
            f"/api/v1/pages/{test_page.id}?hard_delete=true",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Page should be gone
        response = await client.get(f"/api/v1/pages/{test_page.id}", headers=auth_headers)
        assert response.status_code == 404


class TestPageTenantIsolation:
    """Test multi-tenant isolation for pages."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_tenant_page(
        self, client: AsyncClient, auth_headers: dict, db_session
    ):
        """Test pages from other tenants are not visible."""
        # Create a different tenant
        other_tenant = Tenant(
            id=uuid4(), name="Other Tenant", slug="other-tenant-page", settings={}
        )
        db_session.add(other_tenant)
        await db_session.flush()

        # Create a page for the other tenant
        other_page = Page(
            id=uuid4(),
            tenant_id=other_tenant.id,
            slug="other-privacy",
            title="Other Privacy",
            content="Other content",
            page_type=PageType.POLICY.value,
            is_published=True,
        )
        db_session.add(other_page)
        await db_session.commit()

        # Try to access other tenant's page
        response = await client.get(f"/api/v1/pages/{other_page.id}", headers=auth_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_only_shows_own_tenant_pages(
        self, client: AsyncClient, auth_headers: dict, test_page: Page, db_session
    ):
        """Test page list only returns pages from current tenant."""
        # Create another tenant with pages
        other_tenant = Tenant(
            id=uuid4(), name="Other Tenant", slug="other-tenant-page-2", settings={}
        )
        db_session.add(other_tenant)
        await db_session.flush()

        other_page = Page(
            id=uuid4(),
            tenant_id=other_tenant.id,
            slug="hidden-page",
            title="Hidden Page",
            content="Hidden content",
            page_type=PageType.POLICY.value,
            is_published=True,
        )
        db_session.add(other_page)
        await db_session.commit()

        # Get page list
        response = await client.get("/api/v1/pages", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        page_ids = [p["id"] for p in data["pages"]]
        assert str(other_page.id) not in page_ids


class TestPageValidation:
    """Test page validation."""

    @pytest.mark.asyncio
    async def test_create_page_empty_title_fails(self, client: AsyncClient, auth_headers: dict):
        """Test creating page with empty title fails."""
        response = await client.post(
            "/api/v1/pages",
            headers=auth_headers,
            json={
                "title": "",
                "content": "Some content",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_page_invalid_type(self, client: AsyncClient, auth_headers: dict):
        """Test creating page with invalid type fails."""
        response = await client.post(
            "/api/v1/pages",
            headers=auth_headers,
            json={
                "title": "Test Page",
                "content": "Content",
                "page_type": "invalid_type",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_page_valid_types(self, client: AsyncClient, auth_headers: dict):
        """Test creating pages with valid types."""
        for page_type in ["policy", "info", "legal"]:
            response = await client.post(
                "/api/v1/pages",
                headers=auth_headers,
                json={
                    "title": f"Test {page_type.title()} Page",
                    "content": f"{page_type} content",
                    "page_type": page_type,
                },
            )
            assert response.status_code == 201
            data = response.json()
            assert data["page_type"] == page_type
