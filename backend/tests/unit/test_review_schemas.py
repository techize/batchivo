"""
Tests for product review Pydantic schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.review import (
    ProductReviewStats,
    ReviewCreate,
    ReviewHelpfulResponse,
    ReviewListResponse,
    ReviewReject,
    ReviewUpdate,
)
from uuid import uuid4


class TestReviewCreate:
    def test_valid_minimal(self):
        r = ReviewCreate(
            rating=5,
            body="This dragon is absolutely amazing!",
            customer_name="Alice",
            customer_email="alice@example.com",
        )
        assert r.rating == 5
        assert r.title is None

    def test_valid_with_title(self):
        r = ReviewCreate(
            rating=4,
            title="Great quality",
            body="Very happy with this product.",
            customer_name="Bob",
            customer_email="bob@example.com",
        )
        assert r.title == "Great quality"

    def test_rating_minimum(self):
        r = ReviewCreate(
            rating=1,
            body="Not great but ok really I suppose",
            customer_name="C",
            customer_email="c@example.com",
        )
        assert r.rating == 1

    def test_rating_maximum(self):
        r = ReviewCreate(
            rating=5,
            body="Absolutely perfect purchase today!",
            customer_name="D",
            customer_email="d@example.com",
        )
        assert r.rating == 5

    def test_rating_below_minimum_raises(self):
        with pytest.raises(ValidationError):
            ReviewCreate(
                rating=0,
                body="Valid body length here",
                customer_name="E",
                customer_email="e@example.com",
            )

    def test_rating_above_maximum_raises(self):
        with pytest.raises(ValidationError):
            ReviewCreate(
                rating=6,
                body="Valid body length here",
                customer_name="F",
                customer_email="f@example.com",
            )

    def test_body_too_short_raises(self):
        with pytest.raises(ValidationError):
            ReviewCreate(
                rating=3,
                body="Too short",
                customer_name="G",
                customer_email="g@example.com",
            )

    def test_body_exactly_10_chars(self):
        r = ReviewCreate(
            rating=3,
            body="1234567890",
            customer_name="H",
            customer_email="h@example.com",
        )
        assert len(r.body) == 10

    def test_body_too_long_raises(self):
        with pytest.raises(ValidationError):
            ReviewCreate(
                rating=3,
                body="x" * 5001,
                customer_name="I",
                customer_email="i@example.com",
            )

    def test_title_too_long_raises(self):
        with pytest.raises(ValidationError):
            ReviewCreate(
                rating=3,
                title="t" * 201,
                body="Valid body text here.",
                customer_name="J",
                customer_email="j@example.com",
            )

    def test_customer_name_empty_raises(self):
        with pytest.raises(ValidationError):
            ReviewCreate(
                rating=3,
                body="Valid body text here.",
                customer_name="",
                customer_email="k@example.com",
            )

    def test_invalid_email_raises(self):
        with pytest.raises(ValidationError):
            ReviewCreate(
                rating=3,
                body="Valid body text here.",
                customer_name="L",
                customer_email="not-an-email",
            )

    def test_customer_name_max_255(self):
        r = ReviewCreate(
            rating=4,
            body="This product is really great and well made.",
            customer_name="A" * 255,
            customer_email="long@example.com",
        )
        assert len(r.customer_name) == 255

    def test_customer_name_too_long_raises(self):
        with pytest.raises(ValidationError):
            ReviewCreate(
                rating=4,
                body="Valid review body text here.",
                customer_name="A" * 256,
                customer_email="m@example.com",
            )


class TestReviewReject:
    def test_no_reason(self):
        r = ReviewReject()
        assert r.reason is None

    def test_with_reason(self):
        r = ReviewReject(reason="Inappropriate language")
        assert r.reason == "Inappropriate language"

    def test_reason_too_long_raises(self):
        with pytest.raises(ValidationError):
            ReviewReject(reason="r" * 501)

    def test_reason_exactly_500_chars(self):
        r = ReviewReject(reason="r" * 500)
        assert len(r.reason) == 500


class TestReviewUpdate:
    def test_all_none_by_default(self):
        u = ReviewUpdate()
        assert u.title is None
        assert u.body is None
        assert u.is_approved is None
        assert u.rejection_reason is None

    def test_partial_update(self):
        u = ReviewUpdate(is_approved=True)
        assert u.is_approved is True
        assert u.title is None

    def test_body_too_short_raises(self):
        with pytest.raises(ValidationError):
            ReviewUpdate(body="Short")

    def test_body_exactly_10_chars(self):
        u = ReviewUpdate(body="1234567890")
        assert u.body == "1234567890"


class TestReviewListResponse:
    def test_empty_list(self):
        resp = ReviewListResponse(items=[], total=0)
        assert resp.items == []
        assert resp.average_rating is None
        assert resp.rating_distribution is None

    def test_with_distribution(self):
        resp = ReviewListResponse(
            items=[],
            total=10,
            average_rating="4.5",
            rating_distribution={5: 6, 4: 2, 3: 1, 2: 0, 1: 1},
        )
        assert resp.rating_distribution[5] == 6


class TestReviewHelpfulResponse:
    def test_helpful_response(self):
        review_id = uuid4()
        r = ReviewHelpfulResponse(review_id=review_id, helpful_count=7)
        assert r.review_id == review_id
        assert r.helpful_count == 7


class TestProductReviewStats:
    def test_default_values(self):
        stats = ProductReviewStats()
        assert stats.average_rating is None
        assert stats.review_count == 0
        assert stats.rating_distribution is None

    def test_with_data(self):
        stats = ProductReviewStats(
            average_rating="4.2",
            review_count=15,
            rating_distribution={5: 8, 4: 4, 3: 2, 2: 0, 1: 1},
        )
        assert stats.review_count == 15
        assert stats.rating_distribution[1] == 1
