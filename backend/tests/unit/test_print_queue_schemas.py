"""
Tests for PrintQueue Pydantic schemas.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.print_job import JobPriority, JobStatus, PrinterStatus
from app.schemas.print_queue import (
    AutoAssignResult,
    ModelSummary,
    PrintJobAssign,
    PrintJobBase,
    PrintJobCreate,
    PrintJobListResponse,
    PrintJobStatusUpdate,
    PrintJobUpdate,
    PrinterQueueStats,
    PrinterStatusUpdate,
    ProductSummary,
    QueueOverview,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestEnums:
    def test_job_priority_values(self):
        assert JobPriority.LOW == "low"
        assert JobPriority.NORMAL == "normal"
        assert JobPriority.HIGH == "high"
        assert JobPriority.URGENT == "urgent"

    def test_job_status_values(self):
        assert JobStatus.PENDING == "pending"
        assert JobStatus.QUEUED == "queued"
        assert JobStatus.PRINTING == "printing"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"

    def test_printer_status_values(self):
        assert PrinterStatus.IDLE == "idle"
        assert PrinterStatus.PRINTING == "printing"
        assert PrinterStatus.PAUSED == "paused"
        assert PrinterStatus.ERROR == "error"
        assert PrinterStatus.OFFLINE == "offline"
        assert PrinterStatus.MAINTENANCE == "maintenance"


class TestModelSummary:
    def test_valid(self):
        m = ModelSummary(id=uuid4(), sku="MDL-001", name="Dragon V2")
        assert m.sku == "MDL-001"


class TestProductSummary:
    def test_valid(self):
        p = ProductSummary(id=uuid4(), sku="DRG-001", name="Dragon Mini")
        assert p.sku == "DRG-001"


class TestPrintJobBase:
    def test_defaults(self):
        j = PrintJobBase()
        assert j.quantity == 1
        assert j.priority == JobPriority.NORMAL
        assert j.model_id is None
        assert j.product_id is None
        assert j.estimated_duration_hours is None

    def test_quantity_minimum_1(self):
        with pytest.raises(ValidationError):
            PrintJobBase(quantity=0)

    def test_quantity_maximum_100(self):
        j = PrintJobBase(quantity=100)
        assert j.quantity == 100

    def test_quantity_above_100_raises(self):
        with pytest.raises(ValidationError):
            PrintJobBase(quantity=101)

    def test_estimated_duration_hours_zero(self):
        j = PrintJobBase(estimated_duration_hours=Decimal("0"))
        assert j.estimated_duration_hours == Decimal("0")

    def test_estimated_duration_hours_max(self):
        j = PrintJobBase(estimated_duration_hours=Decimal("999"))
        assert j.estimated_duration_hours == Decimal("999")

    def test_estimated_duration_hours_above_max_raises(self):
        with pytest.raises(ValidationError):
            PrintJobBase(estimated_duration_hours=Decimal("1000"))

    def test_reference_max_100(self):
        j = PrintJobBase(reference="R" * 100)
        assert len(j.reference) == 100

    def test_reference_too_long_raises(self):
        with pytest.raises(ValidationError):
            PrintJobBase(reference="R" * 101)

    def test_notes_max_1000(self):
        j = PrintJobBase(notes="N" * 1000)
        assert len(j.notes) == 1000

    def test_notes_too_long_raises(self):
        with pytest.raises(ValidationError):
            PrintJobBase(notes="N" * 1001)

    def test_with_model_and_product(self):
        j = PrintJobBase(
            model_id=uuid4(),
            product_id=uuid4(),
            quantity=3,
            priority=JobPriority.HIGH,
        )
        assert j.quantity == 3
        assert j.priority == JobPriority.HIGH


class TestPrintJobCreate:
    def test_inherits_base_defaults(self):
        j = PrintJobCreate()
        assert j.quantity == 1
        assert j.priority == JobPriority.NORMAL


class TestPrintJobUpdate:
    def test_all_optional(self):
        u = PrintJobUpdate()
        assert u.priority is None
        assert u.reference is None
        assert u.notes is None

    def test_partial_update(self):
        u = PrintJobUpdate(priority=JobPriority.URGENT, notes="Rush order")
        assert u.priority == JobPriority.URGENT

    def test_estimated_duration_above_max_raises(self):
        with pytest.raises(ValidationError):
            PrintJobUpdate(estimated_duration_hours=Decimal("1000"))

    def test_reference_too_long_raises(self):
        with pytest.raises(ValidationError):
            PrintJobUpdate(reference="R" * 101)


class TestPrintJobAssign:
    def test_valid(self):
        a = PrintJobAssign(printer_id=uuid4())
        assert a.printer_id is not None

    def test_required(self):
        with pytest.raises(ValidationError):
            PrintJobAssign()


class TestPrintJobStatusUpdate:
    def test_valid(self):
        u = PrintJobStatusUpdate(status=JobStatus.QUEUED)
        assert u.status == JobStatus.QUEUED
        assert u.error_message is None

    def test_failed_with_error(self):
        u = PrintJobStatusUpdate(status=JobStatus.FAILED, error_message="Nozzle jam")
        assert u.error_message == "Nozzle jam"

    def test_error_message_max_1000(self):
        u = PrintJobStatusUpdate(status=JobStatus.FAILED, error_message="E" * 1000)
        assert len(u.error_message) == 1000

    def test_error_message_too_long_raises(self):
        with pytest.raises(ValidationError):
            PrintJobStatusUpdate(status=JobStatus.FAILED, error_message="E" * 1001)


class TestPrintJobListResponse:
    def test_empty(self):
        r = PrintJobListResponse(items=[], total=0, page=1, page_size=20, pages=0)
        assert r.total == 0
        assert r.pages == 0

    def test_paginated(self):
        r = PrintJobListResponse(items=[], total=100, page=2, page_size=20, pages=5)
        assert r.pages == 5


class TestPrinterQueueStats:
    def test_valid(self):
        s = PrinterQueueStats(
            printer_id=uuid4(),
            printer_name="Bambu X1C",
            current_status=PrinterStatus.IDLE,
            jobs_in_queue=3,
            estimated_time_to_completion_hours=Decimal("4.5"),
        )
        assert s.jobs_in_queue == 3
        assert s.current_job is None


class TestQueueOverview:
    def test_valid(self):
        o = QueueOverview(
            total_pending_jobs=5,
            total_queued_jobs=3,
            total_printing_jobs=2,
            idle_printers=1,
            busy_printers=2,
            printer_stats=[],
        )
        assert o.total_pending_jobs == 5
        assert o.idle_printers == 1


class TestAutoAssignResult:
    def test_valid(self):
        r = AutoAssignResult(
            assigned_count=3,
            assignments=[{"job_id": "j1", "printer_id": "p1", "printer_name": "Bambu"}],
            unassigned_count=1,
            unassigned_reasons=["No idle printers"],
        )
        assert r.assigned_count == 3
        assert len(r.assignments) == 1

    def test_empty(self):
        r = AutoAssignResult(
            assigned_count=0,
            assignments=[],
            unassigned_count=2,
            unassigned_reasons=["No printers available", "Job already assigned"],
        )
        assert r.unassigned_count == 2


class TestPrinterStatusUpdate:
    def test_valid(self):
        u = PrinterStatusUpdate(current_status=PrinterStatus.PRINTING)
        assert u.current_status == PrinterStatus.PRINTING
        assert u.current_job_id is None

    def test_with_job(self):
        jid = uuid4()
        u = PrinterStatusUpdate(current_status=PrinterStatus.PRINTING, current_job_id=jid)
        assert u.current_job_id == jid
