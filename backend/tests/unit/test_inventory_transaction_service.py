"""
Tests for inventory transaction service.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory_transaction import TransactionType
from app.models.spool import Spool
from app.models.tenant import Tenant
from app.models.user import User
from app.services.inventory_transaction import InventoryTransactionService


class TestInventoryTransactionService:
    """Tests for InventoryTransactionService."""

    @pytest.mark.asyncio
    async def test_create_transaction(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
        test_spool: Spool,
    ):
        """Test creating a basic inventory transaction."""
        service = InventoryTransactionService(db_session, test_tenant, test_user)

        transaction = await service.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.USAGE,
            weight_before=Decimal("800"),
            weight_change=Decimal("-50"),
            description="Test usage transaction",
        )

        assert transaction is not None
        assert transaction.id is not None
        assert transaction.tenant_id == test_tenant.id
        assert transaction.spool_id == test_spool.id
        assert transaction.transaction_type == TransactionType.USAGE
        assert transaction.weight_before == Decimal("800")
        assert transaction.weight_change == Decimal("-50")
        assert transaction.weight_after == Decimal("750")
        assert transaction.user_id == test_user.id
        assert transaction.description == "Test usage transaction"

    @pytest.mark.asyncio
    async def test_create_transaction_without_user(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_spool: Spool,
    ):
        """Test creating a transaction without a user (system transaction)."""
        service = InventoryTransactionService(db_session, test_tenant, user=None)

        transaction = await service.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.ADJUSTMENT,
            weight_before=Decimal("500"),
            weight_change=Decimal("100"),
            description="System adjustment",
        )

        assert transaction.user_id is None

    @pytest.mark.asyncio
    async def test_create_transaction_with_notes(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
        test_spool: Spool,
    ):
        """Test creating a transaction with notes."""
        service = InventoryTransactionService(db_session, test_tenant, test_user)

        transaction = await service.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.USAGE,
            weight_before=Decimal("800"),
            weight_change=Decimal("-48.2"),
            description="Production usage",
            notes="Test notes for this transaction",
        )

        assert transaction.notes == "Test notes for this transaction"

    @pytest.mark.asyncio
    async def test_get_transaction(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
        test_spool: Spool,
    ):
        """Test getting a transaction by ID."""
        service = InventoryTransactionService(db_session, test_tenant, test_user)

        # Create transaction
        created = await service.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.USAGE,
            weight_before=Decimal("800"),
            weight_change=Decimal("-25"),
            description="Test transaction",
        )
        await db_session.commit()

        # Retrieve it
        fetched = await service.get_transaction(created.id)

        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.description == "Test transaction"

    @pytest.mark.asyncio
    async def test_get_nonexistent_transaction(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ):
        """Test getting a transaction that doesn't exist."""
        service = InventoryTransactionService(db_session, test_tenant, test_user)

        result = await service.get_transaction(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_list_transactions(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
        test_spool: Spool,
    ):
        """Test listing transactions with pagination."""
        service = InventoryTransactionService(db_session, test_tenant, test_user)

        # Create multiple transactions
        for i in range(5):
            await service.create_transaction(
                spool_id=test_spool.id,
                transaction_type=TransactionType.USAGE,
                weight_before=Decimal("800") - (i * 10),
                weight_change=Decimal("-10"),
                description=f"Transaction {i}",
            )
        await db_session.commit()

        # List all
        transactions, total = await service.list_transactions()
        assert total == 5
        assert len(transactions) == 5

    @pytest.mark.asyncio
    async def test_list_transactions_pagination(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
        test_spool: Spool,
    ):
        """Test listing transactions with pagination."""
        service = InventoryTransactionService(db_session, test_tenant, test_user)

        # Create 10 transactions
        for i in range(10):
            await service.create_transaction(
                spool_id=test_spool.id,
                transaction_type=TransactionType.USAGE,
                weight_before=Decimal("800") - (i * 5),
                weight_change=Decimal("-5"),
                description=f"Transaction {i}",
            )
        await db_session.commit()

        # Get page 1
        page1, total = await service.list_transactions(page=1, page_size=3)
        assert total == 10
        assert len(page1) == 3

        # Get page 2
        page2, _ = await service.list_transactions(page=2, page_size=3)
        assert len(page2) == 3

        # Verify pages have different transactions
        page1_ids = {t.id for t in page1}
        page2_ids = {t.id for t in page2}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_list_transactions_filter_by_spool(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
        test_spool: Spool,
        test_material_type,
    ):
        """Test filtering transactions by spool."""
        service = InventoryTransactionService(db_session, test_tenant, test_user)

        # Create another spool
        other_spool = Spool(
            id=uuid4(),
            tenant_id=test_tenant.id,
            material_type_id=test_material_type.id,
            spool_id="OTHER-SPOOL-001",
            brand="Other Brand",
            color="Blue",
            initial_weight=1000.0,
            current_weight=900.0,
            is_active=True,
        )
        db_session.add(other_spool)
        await db_session.commit()

        # Create transactions for both spools
        await service.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.USAGE,
            weight_before=Decimal("800"),
            weight_change=Decimal("-10"),
            description="First spool transaction",
        )
        await service.create_transaction(
            spool_id=other_spool.id,
            transaction_type=TransactionType.USAGE,
            weight_before=Decimal("900"),
            weight_change=Decimal("-20"),
            description="Other spool transaction",
        )
        await db_session.commit()

        # Filter by first spool
        transactions, total = await service.list_transactions(spool_id=test_spool.id)
        assert total == 1
        assert transactions[0].spool_id == test_spool.id

    @pytest.mark.asyncio
    async def test_list_transactions_filter_by_type(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
        test_spool: Spool,
    ):
        """Test filtering transactions by type."""
        service = InventoryTransactionService(db_session, test_tenant, test_user)

        # Create different transaction types
        await service.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.USAGE,
            weight_before=Decimal("800"),
            weight_change=Decimal("-10"),
            description="Usage",
        )
        await service.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.ADJUSTMENT,
            weight_before=Decimal("790"),
            weight_change=Decimal("50"),
            description="Adjustment",
        )
        await db_session.commit()

        # Filter by USAGE type
        transactions, total = await service.list_transactions(
            transaction_type=TransactionType.USAGE
        )
        assert total == 1
        assert transactions[0].transaction_type == TransactionType.USAGE

    @pytest.mark.asyncio
    async def test_list_transactions_filter_by_date_range(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
        test_spool: Spool,
    ):
        """Test filtering transactions by date range."""
        service = InventoryTransactionService(db_session, test_tenant, test_user)

        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        # Create transaction
        await service.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.USAGE,
            weight_before=Decimal("800"),
            weight_change=Decimal("-10"),
            description="Today's transaction",
        )
        await db_session.commit()

        # Filter with date range that includes today
        transactions, total = await service.list_transactions(
            start_date=yesterday, end_date=tomorrow
        )
        assert total == 1

        # Filter with date range that excludes today
        far_future = now + timedelta(days=10)
        transactions, total = await service.list_transactions(
            start_date=tomorrow, end_date=far_future
        )
        assert total == 0

    @pytest.mark.asyncio
    async def test_create_adjustment_transaction(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
        test_spool: Spool,
    ):
        """Test creating an adjustment transaction."""
        service = InventoryTransactionService(db_session, test_tenant, test_user)

        original_weight = test_spool.current_weight
        new_weight = Decimal("900")

        transaction = await service.create_adjustment_transaction(
            spool=test_spool,
            new_weight=new_weight,
            reason="Manual weight correction after scale calibration",
            notes="Scale was reading 100g low",
        )
        await db_session.commit()

        assert transaction.transaction_type == TransactionType.ADJUSTMENT
        assert transaction.weight_before == Decimal(str(original_weight))
        assert transaction.weight_change == new_weight - Decimal(str(original_weight))
        assert transaction.weight_after == new_weight
        assert "Manual adjustment" in transaction.description
        assert transaction.notes == "Scale was reading 100g low"

        # Verify spool weight was updated
        await db_session.refresh(test_spool)
        assert test_spool.current_weight == float(new_weight)

    @pytest.mark.asyncio
    async def test_get_spool_transaction_summary(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
        test_spool: Spool,
    ):
        """Test getting transaction summary for a spool."""
        service = InventoryTransactionService(db_session, test_tenant, test_user)

        # Create various transactions
        await service.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.USAGE,
            weight_before=Decimal("800"),
            weight_change=Decimal("-50"),
            description="Usage 1",
        )
        await service.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.USAGE,
            weight_before=Decimal("750"),
            weight_change=Decimal("-30"),
            description="Usage 2",
        )
        await service.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.RETURN,
            weight_before=Decimal("720"),
            weight_change=Decimal("20"),
            description="Return from failed print",
        )
        await service.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.ADJUSTMENT,
            weight_before=Decimal("740"),
            weight_change=Decimal("10"),
            description="Scale recalibration",
        )
        await db_session.commit()

        summary = await service.get_spool_transaction_summary(test_spool.id)

        assert summary["spool_id"] == str(test_spool.id)
        assert summary["total_transactions"] == 4
        assert summary["total_used"] == 80.0  # 50 + 30
        assert summary["total_returned"] == 20.0
        assert summary["total_adjusted"] == 10.0
        assert "usage" in summary["by_type"]
        assert summary["by_type"]["usage"]["count"] == 2
        assert summary["by_type"]["return"]["count"] == 1
        assert summary["by_type"]["adjustment"]["count"] == 1

    @pytest.mark.asyncio
    async def test_reversal_transaction(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
        test_spool: Spool,
    ):
        """Test creating a reversal transaction."""
        service = InventoryTransactionService(db_session, test_tenant, test_user)

        # Create original transaction
        original = await service.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.USAGE,
            weight_before=Decimal("800"),
            weight_change=Decimal("-50"),
            description="Original usage",
        )
        await db_session.commit()

        # Create reversal
        reversal = await service.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.RETURN,
            weight_before=Decimal("750"),
            weight_change=Decimal("50"),
            description="Reversal of original usage",
            reversal_of_id=original.id,
            is_reversal=True,
        )
        await db_session.commit()

        assert reversal.is_reversal is True
        assert reversal.reversal_of_id == original.id


class TestTransactionIsolation:
    """Tests for tenant isolation in transactions."""

    @pytest.mark.asyncio
    async def test_transactions_isolated_by_tenant(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_spool: Spool,
    ):
        """Test that transactions from other tenants are not visible."""
        # Create a second tenant
        other_tenant = Tenant(
            id=uuid4(),
            name="Other Tenant",
            slug="other-tenant",
            settings={},
        )
        db_session.add(other_tenant)
        await db_session.commit()

        # Create transaction with first tenant
        service1 = InventoryTransactionService(db_session, test_tenant)
        await service1.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.USAGE,
            weight_before=Decimal("800"),
            weight_change=Decimal("-10"),
            description="Tenant 1 transaction",
        )
        await db_session.commit()

        # List transactions with second tenant - should be empty
        service2 = InventoryTransactionService(db_session, other_tenant)
        transactions, total = await service2.list_transactions()

        assert total == 0
        assert len(transactions) == 0

        # List with first tenant - should see the transaction
        transactions, total = await service1.list_transactions()
        assert total == 1

    @pytest.mark.asyncio
    async def test_get_transaction_tenant_isolation(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_spool: Spool,
    ):
        """Test that getting transaction respects tenant isolation."""
        # Create second tenant
        other_tenant = Tenant(
            id=uuid4(),
            name="Other Tenant",
            slug="other-tenant",
            settings={},
        )
        db_session.add(other_tenant)
        await db_session.commit()

        # Create transaction with first tenant
        service1 = InventoryTransactionService(db_session, test_tenant)
        transaction = await service1.create_transaction(
            spool_id=test_spool.id,
            transaction_type=TransactionType.USAGE,
            weight_before=Decimal("800"),
            weight_change=Decimal("-10"),
            description="Private transaction",
        )
        await db_session.commit()

        # Try to get with other tenant
        service2 = InventoryTransactionService(db_session, other_tenant)
        result = await service2.get_transaction(transaction.id)

        assert result is None
