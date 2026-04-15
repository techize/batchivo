"""
Tests for External Listing Pydantic schemas.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.external_listing import (
    ExternalListingBase,
    ExternalListingCreate,
    ExternalListingResponse,
    ProductSyncStatusResponse,
    SyncStatusChannel,
    SyncToEtsyRequest,
    SyncToEtsyResponse,
    SyncToShopifyRequest,
    SyncToShopifyResponse,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestExternalListingBase:
    def test_valid_minimal(self):
        e = ExternalListingBase(platform="etsy", external_id="123456")
        assert e.platform == "etsy"
        assert e.external_id == "123456"
        assert e.external_url is None

    def test_with_url(self):
        e = ExternalListingBase(
            platform="amazon",
            external_id="B0001",
            external_url="https://amazon.com/dp/B0001",
        )
        assert e.external_url == "https://amazon.com/dp/B0001"

    def test_platform_required(self):
        with pytest.raises(ValidationError):
            ExternalListingBase(external_id="123")

    def test_external_id_required(self):
        with pytest.raises(ValidationError):
            ExternalListingBase(platform="etsy")


class TestExternalListingCreate:
    def test_valid(self):
        c = ExternalListingCreate(platform="shopify", external_id="gid://shopify/Product/42")
        assert c.platform == "shopify"

    def test_with_url(self):
        c = ExternalListingCreate(
            platform="ebay",
            external_id="ebay-9876",
            external_url="https://www.ebay.com/itm/9876",
        )
        assert c.external_url == "https://www.ebay.com/itm/9876"


class TestExternalListingResponse:
    def _base(self, **kwargs) -> dict:
        defaults = {
            "id": uuid4(),
            "product_id": uuid4(),
            "platform": "etsy",
            "external_id": "etsy-123",
            "sync_status": "synced",
            "created_at": _now(),
            "updated_at": _now(),
        }
        defaults.update(kwargs)
        return defaults

    def test_valid_minimal(self):
        r = ExternalListingResponse(**self._base())
        assert r.sync_status == "synced"
        assert r.last_synced_at is None
        assert r.last_sync_error is None

    def test_with_all_fields(self):
        ts = _now()
        r = ExternalListingResponse(
            **self._base(
                last_synced_at=ts,
                last_sync_error=None,
                external_url="https://etsy.com/listing/123",
            )
        )
        assert r.last_synced_at == ts

    def test_with_sync_error(self):
        r = ExternalListingResponse(**self._base(sync_status="error", last_sync_error="Timeout"))
        assert r.last_sync_error == "Timeout"


class TestSyncToEtsyRequest:
    def test_default_force_false(self):
        r = SyncToEtsyRequest()
        assert r.force is False

    def test_force_true(self):
        r = SyncToEtsyRequest(force=True)
        assert r.force is True


class TestSyncToEtsyResponse:
    def _listing(self) -> ExternalListingResponse:
        return ExternalListingResponse(
            id=uuid4(),
            product_id=uuid4(),
            platform="etsy",
            external_id="etsy-1",
            sync_status="synced",
            created_at=_now(),
            updated_at=_now(),
        )

    def test_success_no_listing(self):
        r = SyncToEtsyResponse(success=True, message="OK")
        assert r.listing is None
        assert r.etsy_url is None

    def test_success_with_listing(self):
        listing = self._listing()
        r = SyncToEtsyResponse(
            success=True,
            message="Synced",
            listing=listing,
            etsy_url="https://etsy.com/listing/1",
        )
        assert r.listing.platform == "etsy"
        assert r.etsy_url == "https://etsy.com/listing/1"

    def test_failure(self):
        r = SyncToEtsyResponse(success=False, message="Rate limited")
        assert r.success is False


class TestSyncToShopifyRequest:
    def test_default_force_false(self):
        r = SyncToShopifyRequest()
        assert r.force is False

    def test_force_true(self):
        r = SyncToShopifyRequest(force=True)
        assert r.force is True


class TestSyncToShopifyResponse:
    def test_success(self):
        r = SyncToShopifyResponse(
            success=True, message="Done", shopify_url="https://shop.myshopify.com/products/1"
        )
        assert r.shopify_url == "https://shop.myshopify.com/products/1"
        assert r.listing is None

    def test_failure(self):
        r = SyncToShopifyResponse(success=False, message="Auth error")
        assert r.success is False


class TestSyncStatusChannel:
    def test_synced(self):
        c = SyncStatusChannel(synced=True, external_url="https://etsy.com/1", sync_status="synced")
        assert c.synced is True
        assert c.sync_status == "synced"

    def test_not_synced_defaults(self):
        c = SyncStatusChannel(synced=False)
        assert c.last_synced_at is None
        assert c.external_url is None
        assert c.sync_status is None
        assert c.last_sync_error is None


class TestProductSyncStatusResponse:
    def _channel(self, synced: bool = False) -> SyncStatusChannel:
        return SyncStatusChannel(synced=synced)

    def test_valid(self):
        pid = uuid4()
        r = ProductSyncStatusResponse(
            product_id=pid,
            shop=self._channel(synced=True),
            shopify=self._channel(),
            etsy=self._channel(),
        )
        assert r.product_id == pid
        assert r.shop.synced is True
        assert r.shopify.synced is False

    def test_all_channels_required(self):
        with pytest.raises(ValidationError):
            ProductSyncStatusResponse(
                product_id=uuid4(),
                shop=self._channel(),
                shopify=self._channel(),
                # etsy missing
            )
