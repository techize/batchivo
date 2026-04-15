"""
Tests for audit log Pydantic schemas.
"""

from uuid import uuid4


from app.schemas.audit import AuditLogFilters, AuditLogListResponse, AuditLogSummary


class TestAuditLogFilters:
    def test_all_optional(self):
        f = AuditLogFilters()
        assert f.action is None
        assert f.entity_type is None
        assert f.user_id is None
        assert f.start_date is None

    def test_entity_id_filter(self):
        eid = uuid4()
        f = AuditLogFilters(entity_id=eid)
        assert f.entity_id == eid

    def test_entity_type_filter(self):
        f = AuditLogFilters(entity_type="product")
        assert f.entity_type == "product"

    def test_user_id_and_customer_id(self):
        uid = uuid4()
        cid = uuid4()
        f = AuditLogFilters(user_id=uid, customer_id=cid)
        assert f.user_id == uid
        assert f.customer_id == cid

    def test_ip_address_filter(self):
        f = AuditLogFilters(ip_address="192.168.1.1")
        assert f.ip_address == "192.168.1.1"


class TestAuditLogListResponse:
    def test_empty_list(self):
        r = AuditLogListResponse(items=[], total=0, page=1, page_size=20, total_pages=0)
        assert r.items == []
        assert r.total == 0

    def test_pagination_fields(self):
        r = AuditLogListResponse(items=[], total=100, page=3, page_size=20, total_pages=5)
        assert r.page == 3
        assert r.page_size == 20
        assert r.total_pages == 5


class TestAuditLogSummary:
    def test_valid_summary(self):
        s = AuditLogSummary(
            total_entries=42,
            actions_breakdown={"create": 20, "update": 15, "delete": 7},
            entity_types_breakdown={"product": 30, "order": 12},
            recent_activity=[],
        )
        assert s.total_entries == 42
        assert s.actions_breakdown["create"] == 20
        assert s.entity_types_breakdown["product"] == 30
        assert s.recent_activity == []

    def test_empty_breakdowns(self):
        s = AuditLogSummary(
            total_entries=0,
            actions_breakdown={},
            entity_types_breakdown={},
            recent_activity=[],
        )
        assert s.total_entries == 0
