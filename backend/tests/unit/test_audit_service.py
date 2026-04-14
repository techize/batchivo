"""Unit tests for audit_service.calculate_changes (pure function)."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.services.audit_service import calculate_changes


class TestCalculateChanges:
    """Tests for calculate_changes standalone function."""

    def test_no_changes_returns_empty_dict(self):
        obj = SimpleNamespace(name="Dragon", price=45.0)
        result = calculate_changes(obj, {"name": "Dragon", "price": 45.0})
        assert result == {}

    def test_single_string_change(self):
        obj = SimpleNamespace(name="Dragon")
        result = calculate_changes(obj, {"name": "Ice Dragon"})
        assert result == {"name": {"old": "Dragon", "new": "Ice Dragon"}}

    def test_single_numeric_change(self):
        obj = SimpleNamespace(price=45.0)
        result = calculate_changes(obj, {"price": 50.0})
        assert result == {"price": {"old": 45.0, "new": 50.0}}

    def test_multiple_fields_changed(self):
        obj = SimpleNamespace(name="Dragon", price=45.0, units=3)
        result = calculate_changes(obj, {"name": "Ice Dragon", "price": 55.0, "units": 3})
        assert "name" in result
        assert "price" in result
        assert "units" not in result  # unchanged

    def test_field_not_on_object_is_ignored(self):
        obj = SimpleNamespace(name="Dragon")
        result = calculate_changes(obj, {"name": "Ice Dragon", "nonexistent_field": "value"})
        assert "nonexistent_field" not in result
        assert "name" in result

    def test_empty_new_data_returns_empty(self):
        obj = SimpleNamespace(name="Dragon", price=45.0)
        result = calculate_changes(obj, {})
        assert result == {}

    def test_datetime_old_value_serialized_to_isoformat(self):
        dt = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        obj = SimpleNamespace(created_at=dt)
        result = calculate_changes(obj, {"created_at": "2025-07-01T00:00:00+00:00"})
        assert result["created_at"]["old"] == dt.isoformat()

    def test_datetime_new_value_serialized_to_isoformat(self):
        old_dt = datetime(2025, 6, 15, tzinfo=timezone.utc)
        new_dt = datetime(2025, 7, 1, tzinfo=timezone.utc)
        obj = SimpleNamespace(created_at=old_dt)
        result = calculate_changes(obj, {"created_at": new_dt})
        assert result["created_at"]["new"] == new_dt.isoformat()

    def test_uuid_old_value_serialized_to_string(self):
        uid = uuid4()
        obj = SimpleNamespace(tenant_id=uid)
        new_uid = uuid4()
        result = calculate_changes(obj, {"tenant_id": new_uid})
        assert result["tenant_id"]["old"] == str(uid)

    def test_uuid_new_value_serialized_to_string(self):
        old_uid = uuid4()
        new_uid = uuid4()
        obj = SimpleNamespace(tenant_id=old_uid)
        result = calculate_changes(obj, {"tenant_id": new_uid})
        assert result["tenant_id"]["new"] == str(new_uid)

    def test_none_old_to_value_detected_as_change(self):
        obj = SimpleNamespace(description=None)
        result = calculate_changes(obj, {"description": "A dragon"})
        assert result == {"description": {"old": None, "new": "A dragon"}}

    def test_value_to_none_detected_as_change(self):
        obj = SimpleNamespace(description="A dragon")
        result = calculate_changes(obj, {"description": None})
        assert result == {"description": {"old": "A dragon", "new": None}}

    def test_same_uuid_produces_no_change(self):
        uid = uuid4()
        obj = SimpleNamespace(tenant_id=uid)
        result = calculate_changes(obj, {"tenant_id": uid})
        assert result == {}

    def test_boolean_change(self):
        obj = SimpleNamespace(is_active=True)
        result = calculate_changes(obj, {"is_active": False})
        assert result == {"is_active": {"old": True, "new": False}}

    def test_false_to_true_change(self):
        obj = SimpleNamespace(is_active=False)
        result = calculate_changes(obj, {"is_active": True})
        assert result == {"is_active": {"old": False, "new": True}}
