"""Tests for audit log API endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.audit_log import AuditAction, AuditLog


class TestAuditEndpoints:
    """Tests for audit API endpoints."""

    @pytest.fixture
    async def audit_logs(self, test_tenant, test_user, db_session):
        """Create sample audit log entries."""
        logs = []

        # Create various audit entries
        log1 = AuditLog(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            action=AuditAction.CREATE,
            entity_type="product",
            entity_id=uuid4(),
            description="Created product",
            ip_address="192.168.1.100",
        )
        db_session.add(log1)
        logs.append(log1)

        log2 = AuditLog(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            action=AuditAction.UPDATE,
            entity_type="product",
            entity_id=log1.entity_id,
            changes={"name": {"old": "Old Name", "new": "New Name"}},
            description="Updated product",
            ip_address="192.168.1.100",
        )
        db_session.add(log2)
        logs.append(log2)

        log3 = AuditLog(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            action=AuditAction.ORDER_CREATED,
            entity_type="order",
            entity_id=uuid4(),
            description="Order created",
            ip_address="192.168.1.101",
        )
        db_session.add(log3)
        logs.append(log3)

        log4 = AuditLog(
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            action=AuditAction.LOGIN,
            entity_type="user",
            entity_id=test_user.id,
            description="Successful login",
            ip_address="192.168.1.102",
        )
        db_session.add(log4)
        logs.append(log4)

        await db_session.commit()
        return logs

    @pytest.mark.asyncio
    async def test_list_audit_logs(
        self,
        client: AsyncClient,
        audit_logs,
    ):
        """Test listing audit logs."""
        response = await client.get("/api/v1/audit")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 4
        assert len(data["items"]) >= 4

        # Check first item structure
        first_item = data["items"][0]
        assert "id" in first_item
        assert "action" in first_item
        assert "entity_type" in first_item
        assert "created_at" in first_item

    @pytest.mark.asyncio
    async def test_list_audit_logs_filter_by_action(
        self,
        client: AsyncClient,
        audit_logs,
    ):
        """Test filtering audit logs by action type."""
        response = await client.get(
            "/api/v1/audit",
            params={"action": "create"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

        # All items should have CREATE action
        for item in data["items"]:
            assert item["action"] == "create"

    @pytest.mark.asyncio
    async def test_list_audit_logs_filter_by_entity_type(
        self,
        client: AsyncClient,
        audit_logs,
    ):
        """Test filtering audit logs by entity type."""
        response = await client.get(
            "/api/v1/audit",
            params={"entity_type": "product"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2

        # All items should have product entity type
        for item in data["items"]:
            assert item["entity_type"] == "product"

    @pytest.mark.asyncio
    async def test_list_audit_logs_filter_by_user(
        self,
        client: AsyncClient,
        audit_logs,
        test_user,
    ):
        """Test filtering audit logs by user ID."""
        response = await client.get(
            "/api/v1/audit",
            params={"user_id": str(test_user.id)},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 4

    @pytest.mark.asyncio
    async def test_list_audit_logs_pagination(
        self,
        client: AsyncClient,
        audit_logs,
    ):
        """Test audit logs pagination."""
        response = await client.get(
            "/api/v1/audit",
            params={"page": 1, "page_size": 2},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert "total_pages" in data

    @pytest.mark.asyncio
    async def test_get_audit_summary(
        self,
        client: AsyncClient,
        audit_logs,
    ):
        """Test getting audit log summary."""
        response = await client.get("/api/v1/audit/summary")

        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data
        assert "actions_breakdown" in data
        assert "entity_types_breakdown" in data
        assert "recent_activity" in data

        assert data["total_entries"] >= 4
        assert "create" in data["actions_breakdown"]
        assert "product" in data["entity_types_breakdown"]

    @pytest.mark.asyncio
    async def test_get_entity_history(
        self,
        client: AsyncClient,
        audit_logs,
    ):
        """Test getting audit history for a specific entity."""
        # Get the product entity_id from the first log
        entity_id = audit_logs[0].entity_id

        response = await client.get(f"/api/v1/audit/entity/product/{entity_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "product"
        assert data["entity_id"] == str(entity_id)
        assert "history" in data
        assert len(data["history"]) >= 2  # CREATE and UPDATE

    @pytest.mark.asyncio
    async def test_get_user_activity(
        self,
        client: AsyncClient,
        audit_logs,
        test_user,
    ):
        """Test getting activity for a specific user."""
        response = await client.get(f"/api/v1/audit/user/{test_user.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(test_user.id)
        assert "activity" in data
        assert len(data["activity"]) >= 4

    @pytest.mark.asyncio
    async def test_list_action_types(
        self,
        client: AsyncClient,
    ):
        """Test listing available action types."""
        response = await client.get("/api/v1/audit/actions")

        assert response.status_code == 200
        data = response.json()
        assert "actions" in data
        assert len(data["actions"]) > 10  # We have many action types

        # Check structure
        first_action = data["actions"][0]
        assert "value" in first_action
        assert "label" in first_action

    @pytest.mark.asyncio
    async def test_audit_log_includes_changes(
        self,
        client: AsyncClient,
        audit_logs,
    ):
        """Test that UPDATE logs include changes."""
        response = await client.get(
            "/api/v1/audit",
            params={"action": "update"},
        )

        assert response.status_code == 200
        data = response.json()

        # Find the update log
        update_log = next((item for item in data["items"] if item["action"] == "update"), None)
        assert update_log is not None
        assert update_log["changes"] is not None
        assert "name" in update_log["changes"]
        assert update_log["changes"]["name"]["old"] == "Old Name"
        assert update_log["changes"]["name"]["new"] == "New Name"

    @pytest.mark.asyncio
    async def test_audit_log_includes_ip_address(
        self,
        client: AsyncClient,
        audit_logs,
    ):
        """Test that logs include IP address."""
        response = await client.get("/api/v1/audit")

        assert response.status_code == 200
        data = response.json()

        # Check that at least one log has IP address
        has_ip = any(item.get("ip_address") is not None for item in data["items"])
        assert has_ip

    @pytest.mark.asyncio
    async def test_filter_by_ip_address(
        self,
        client: AsyncClient,
        audit_logs,
    ):
        """Test filtering audit logs by IP address."""
        response = await client.get(
            "/api/v1/audit",
            params={"ip_address": "192.168.1.100"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2

        # All items should have the specified IP
        for item in data["items"]:
            assert item["ip_address"] == "192.168.1.100"
