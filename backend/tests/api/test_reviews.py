"""Tests for product reviews API endpoints."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.product import Product
from app.models.review import Review


class TestPublicReviewEndpoints:
    """Tests for public (shop) review endpoints."""

    @pytest.mark.asyncio
    async def test_get_product_reviews_empty(
        self,
        unauthenticated_client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test getting reviews for a product with no reviews."""
        # Create a shop-visible product
        product = Product(
            tenant_id=test_tenant.id,
            sku="TEST-REVIEW-001",
            name="Test Product",
            shop_visible=True,
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        response = await unauthenticated_client.get(f"/api/v1/shop/products/{product.id}/reviews")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["data"] == []
        assert data["average_rating"] is None
        assert data["rating_distribution"] == {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}

    @pytest.mark.asyncio
    async def test_get_product_reviews_with_approved(
        self,
        unauthenticated_client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test getting approved reviews for a product."""
        # Create a shop-visible product
        product = Product(
            tenant_id=test_tenant.id,
            sku="TEST-REVIEW-002",
            name="Test Product",
            shop_visible=True,
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Create approved and unapproved reviews
        approved_review = Review(
            tenant_id=test_tenant.id,
            product_id=product.id,
            customer_email="approved@example.com",
            customer_name="Approved Reviewer",
            rating=5,
            title="Great product!",
            body="This is an amazing product. Highly recommend it!",
            is_approved=True,
            approved_at=datetime.now(timezone.utc),
        )
        unapproved_review = Review(
            tenant_id=test_tenant.id,
            product_id=product.id,
            customer_email="pending@example.com",
            customer_name="Pending Reviewer",
            rating=3,
            body="This is a pending review that should not appear.",
            is_approved=False,
        )
        db_session.add(approved_review)
        db_session.add(unapproved_review)
        await db_session.commit()

        response = await unauthenticated_client.get(f"/api/v1/shop/products/{product.id}/reviews")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1  # Only approved review
        assert len(data["data"]) == 1
        assert data["data"][0]["customer_name"] == "Approved Reviewer"
        assert data["data"][0]["rating"] == 5
        assert data["average_rating"] == "5.00"

    @pytest.mark.asyncio
    async def test_submit_review_success(
        self,
        unauthenticated_client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test submitting a review for a product."""
        # Create a shop-visible product
        product = Product(
            tenant_id=test_tenant.id,
            sku="TEST-REVIEW-003",
            name="Test Product",
            shop_visible=True,
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        response = await unauthenticated_client.post(
            f"/api/v1/shop/products/{product.id}/reviews",
            json={
                "rating": 4,
                "title": "Good product",
                "body": "This is a good product. I like it!",
                "customer_name": "Test Reviewer",
                "customer_email": "reviewer@example.com",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "approval" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_submit_review_duplicate_email(
        self,
        unauthenticated_client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test that duplicate reviews from same email are rejected."""
        # Create a shop-visible product
        product = Product(
            tenant_id=test_tenant.id,
            sku="TEST-REVIEW-004",
            name="Test Product",
            shop_visible=True,
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Create existing review
        existing_review = Review(
            tenant_id=test_tenant.id,
            product_id=product.id,
            customer_email="duplicate@example.com",
            customer_name="First Reviewer",
            rating=5,
            body="First review from this email address.",
            is_approved=False,
        )
        db_session.add(existing_review)
        await db_session.commit()

        # Try to submit another review with same email
        response = await unauthenticated_client.post(
            f"/api/v1/shop/products/{product.id}/reviews",
            json={
                "rating": 3,
                "title": "Second review",
                "body": "This should be rejected as duplicate.",
                "customer_name": "Second Reviewer",
                "customer_email": "duplicate@example.com",
            },
        )

        assert response.status_code == 400
        assert "already submitted" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_submit_review_product_not_found(
        self,
        unauthenticated_client: AsyncClient,
    ):
        """Test submitting review for non-existent product."""
        fake_id = uuid4()
        response = await unauthenticated_client.post(
            f"/api/v1/shop/products/{fake_id}/reviews",
            json={
                "rating": 5,
                "body": "This product doesn't exist.",
                "customer_name": "Test Reviewer",
                "customer_email": "test@example.com",
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_review_helpful(
        self,
        unauthenticated_client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test marking a review as helpful."""
        # Create a shop-visible product
        product = Product(
            tenant_id=test_tenant.id,
            sku="TEST-REVIEW-005",
            name="Test Product",
            shop_visible=True,
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Create approved review
        review = Review(
            tenant_id=test_tenant.id,
            product_id=product.id,
            customer_email="helpful@example.com",
            customer_name="Helpful Reviewer",
            rating=5,
            body="This is a helpful review that others should see.",
            is_approved=True,
            approved_at=datetime.now(timezone.utc),
            helpful_count=0,
        )
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        response = await unauthenticated_client.post(
            f"/api/v1/shop/products/{product.id}/reviews/{review.id}/helpful"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["helpful_count"] == 1


class TestAdminReviewEndpoints:
    """Tests for admin review moderation endpoints."""

    @pytest.mark.asyncio
    async def test_list_pending_reviews(
        self,
        client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test listing pending reviews for moderation."""
        # Create a product and reviews
        product = Product(
            tenant_id=test_tenant.id,
            sku="TEST-REVIEW-ADMIN-001",
            name="Admin Test Product",
            shop_visible=True,
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        pending_review = Review(
            tenant_id=test_tenant.id,
            product_id=product.id,
            customer_email="pending@example.com",
            customer_name="Pending Reviewer",
            rating=4,
            body="This review is waiting for approval.",
            is_approved=False,
        )
        approved_review = Review(
            tenant_id=test_tenant.id,
            product_id=product.id,
            customer_email="approved@example.com",
            customer_name="Approved Reviewer",
            rating=5,
            body="This review has been approved.",
            is_approved=True,
            approved_at=datetime.now(timezone.utc),
        )
        db_session.add(pending_review)
        db_session.add(approved_review)
        await db_session.commit()

        response = await client.get("/api/v1/reviews?status=pending")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1  # At least our pending review
        # All returned reviews should be pending (not approved, no rejection reason)
        for review in data["items"]:
            assert review["is_approved"] is False

    @pytest.mark.asyncio
    async def test_approve_review(
        self,
        client: AsyncClient,
        test_tenant,
        test_user,
        db_session,
    ):
        """Test approving a pending review."""
        # Create a product and pending review
        product = Product(
            tenant_id=test_tenant.id,
            sku="TEST-REVIEW-APPROVE-001",
            name="Approval Test Product",
            shop_visible=True,
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        review = Review(
            tenant_id=test_tenant.id,
            product_id=product.id,
            customer_email="toapprove@example.com",
            customer_name="To Approve Reviewer",
            rating=4,
            body="This review should be approved by admin.",
            is_approved=False,
        )
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        response = await client.post(f"/api/v1/reviews/{review.id}/approve")

        assert response.status_code == 200
        data = response.json()
        assert data["is_approved"] is True
        assert data["approved_at"] is not None
        assert data["approved_by"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_reject_review(
        self,
        client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test rejecting a review with reason."""
        # Create a product and pending review
        product = Product(
            tenant_id=test_tenant.id,
            sku="TEST-REVIEW-REJECT-001",
            name="Rejection Test Product",
            shop_visible=True,
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        review = Review(
            tenant_id=test_tenant.id,
            product_id=product.id,
            customer_email="toreject@example.com",
            customer_name="To Reject Reviewer",
            rating=1,
            body="This review contains inappropriate content.",
            is_approved=False,
        )
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        response = await client.post(
            f"/api/v1/reviews/{review.id}/reject",
            json={"reason": "Inappropriate language"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_approved"] is False
        assert data["rejection_reason"] == "Inappropriate language"

    @pytest.mark.asyncio
    async def test_delete_review(
        self,
        client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test deleting a review."""
        # Create a product and review
        product = Product(
            tenant_id=test_tenant.id,
            sku="TEST-REVIEW-DELETE-001",
            name="Delete Test Product",
            shop_visible=True,
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        review = Review(
            tenant_id=test_tenant.id,
            product_id=product.id,
            customer_email="todelete@example.com",
            customer_name="To Delete Reviewer",
            rating=2,
            body="This review should be deleted.",
            is_approved=False,
        )
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)
        review_id = review.id

        response = await client.delete(f"/api/v1/reviews/{review_id}")

        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(f"/api/v1/reviews/{review_id}")
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_cannot_approve_already_approved(
        self,
        client: AsyncClient,
        test_tenant,
        db_session,
    ):
        """Test that approving already approved review fails."""
        # Create a product and approved review
        product = Product(
            tenant_id=test_tenant.id,
            sku="TEST-REVIEW-DOUBLE-001",
            name="Double Approve Test",
            shop_visible=True,
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        review = Review(
            tenant_id=test_tenant.id,
            product_id=product.id,
            customer_email="alreadyapproved@example.com",
            customer_name="Already Approved",
            rating=5,
            body="This review is already approved.",
            is_approved=True,
            approved_at=datetime.now(timezone.utc),
        )
        db_session.add(review)
        await db_session.commit()
        await db_session.refresh(review)

        response = await client.post(f"/api/v1/reviews/{review.id}/approve")

        assert response.status_code == 400
        assert "already approved" in response.json()["detail"]
