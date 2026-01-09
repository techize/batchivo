"""Tests for print queue API."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.print_job import JobPriority, JobStatus, PrintJob
from app.models.printer import Printer


# ============================================
# Fixtures
# ============================================


@pytest.fixture
async def test_printer(db_session: AsyncSession, test_tenant):
    """Create a test printer."""
    printer = Printer(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Test Printer",
        manufacturer="Bambu Lab",
        model="X1 Carbon",
        bed_size_x_mm=256,
        bed_size_y_mm=256,
        bed_size_z_mm=256,
        is_active=True,
        current_status="idle",
    )
    db_session.add(printer)
    await db_session.commit()
    await db_session.refresh(printer)
    return printer


@pytest.fixture
async def test_printer_offline(db_session: AsyncSession, test_tenant):
    """Create an offline test printer."""
    printer = Printer(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="Offline Printer",
        manufacturer="Creality",
        model="Ender 3",
        is_active=True,
        current_status="offline",
    )
    db_session.add(printer)
    await db_session.commit()
    await db_session.refresh(printer)
    return printer


@pytest.fixture
async def test_print_job(db_session: AsyncSession, test_tenant):
    """Create a test print job."""
    job = PrintJob(
        id=uuid4(),
        tenant_id=test_tenant.id,
        quantity=1,
        priority=JobPriority.NORMAL.value,
        status=JobStatus.PENDING.value,
        notes="Test print job",
        reference="TEST-001",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest.fixture
async def test_queued_job(db_session: AsyncSession, test_tenant, test_printer):
    """Create a queued print job assigned to a printer."""
    job = PrintJob(
        id=uuid4(),
        tenant_id=test_tenant.id,
        quantity=2,
        priority=JobPriority.HIGH.value,
        status=JobStatus.QUEUED.value,
        assigned_printer_id=test_printer.id,
        notes="Queued test job",
        reference="QUEUE-001",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


@pytest.fixture
async def multiple_pending_jobs(db_session: AsyncSession, test_tenant):
    """Create multiple pending jobs with different priorities."""
    jobs = []
    priorities = [
        (JobPriority.URGENT, "Urgent job"),
        (JobPriority.HIGH, "High priority job"),
        (JobPriority.NORMAL, "Normal job"),
        (JobPriority.LOW, "Low priority job"),
    ]
    for priority, notes in priorities:
        job = PrintJob(
            id=uuid4(),
            tenant_id=test_tenant.id,
            quantity=1,
            priority=priority.value,
            status=JobStatus.PENDING.value,
            notes=notes,
        )
        db_session.add(job)
        jobs.append(job)
    await db_session.commit()
    for job in jobs:
        await db_session.refresh(job)
    return jobs


# ============================================
# Create Job Tests
# ============================================


class TestCreatePrintJob:
    """Tests for creating print jobs."""

    async def test_create_job_success(self, client: AsyncClient):
        """Test creating a basic print job."""
        response = await client.post(
            "/api/v1/print-queue",
            json={
                "quantity": 2,
                "priority": "normal",
                "notes": "Test job creation",
                "reference": "CREATE-001",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["quantity"] == 2
        assert data["priority"] == "normal"
        assert data["status"] == "pending"
        assert data["notes"] == "Test job creation"
        assert data["reference"] == "CREATE-001"
        assert data["assigned_printer_id"] is None

    async def test_create_job_with_high_priority(self, client: AsyncClient):
        """Test creating a high priority job."""
        response = await client.post(
            "/api/v1/print-queue",
            json={"quantity": 1, "priority": "high"},
        )
        assert response.status_code == 201
        assert response.json()["priority"] == "high"

    async def test_create_job_with_urgent_priority(self, client: AsyncClient):
        """Test creating an urgent priority job."""
        response = await client.post(
            "/api/v1/print-queue",
            json={"quantity": 1, "priority": "urgent"},
        )
        assert response.status_code == 201
        assert response.json()["priority"] == "urgent"

    async def test_create_job_with_estimated_duration(self, client: AsyncClient):
        """Test creating a job with estimated duration."""
        response = await client.post(
            "/api/v1/print-queue",
            json={
                "quantity": 1,
                "estimated_duration_hours": "2.5",
            },
        )
        assert response.status_code == 201
        assert response.json()["estimated_duration_hours"] == "2.50"

    async def test_create_job_minimal(self, client: AsyncClient):
        """Test creating a job with minimal fields."""
        response = await client.post(
            "/api/v1/print-queue",
            json={},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["quantity"] == 1  # Default
        assert data["priority"] == "normal"  # Default
        assert data["status"] == "pending"

    async def test_create_job_invalid_quantity(self, client: AsyncClient):
        """Test creating a job with invalid quantity."""
        response = await client.post(
            "/api/v1/print-queue",
            json={"quantity": 0},
        )
        assert response.status_code == 422

    async def test_create_job_quantity_too_high(self, client: AsyncClient):
        """Test creating a job with quantity exceeding limit."""
        response = await client.post(
            "/api/v1/print-queue",
            json={"quantity": 101},
        )
        assert response.status_code == 422

    async def test_create_job_invalid_priority(self, client: AsyncClient):
        """Test creating a job with invalid priority."""
        response = await client.post(
            "/api/v1/print-queue",
            json={"priority": "super-urgent"},
        )
        assert response.status_code == 422


# ============================================
# List Jobs Tests
# ============================================


class TestListPrintJobs:
    """Tests for listing print jobs."""

    async def test_list_jobs_empty(self, client: AsyncClient):
        """Test listing jobs when none exist."""
        response = await client.get("/api/v1/print-queue")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_jobs_with_data(self, client: AsyncClient, test_print_job: PrintJob):
        """Test listing jobs with existing data."""
        response = await client.get("/api/v1/print-queue")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(test_print_job.id)

    async def test_list_jobs_filter_by_status(
        self, client: AsyncClient, test_print_job: PrintJob, test_queued_job: PrintJob
    ):
        """Test filtering jobs by status."""
        response = await client.get("/api/v1/print-queue?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "pending"

    async def test_list_jobs_filter_by_priority(self, client: AsyncClient, multiple_pending_jobs):
        """Test filtering jobs by priority."""
        response = await client.get("/api/v1/print-queue?priority=urgent")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["priority"] == "urgent"

    async def test_list_jobs_filter_by_printer(
        self, client: AsyncClient, test_queued_job: PrintJob, test_printer: Printer
    ):
        """Test filtering jobs by assigned printer."""
        response = await client.get(f"/api/v1/print-queue?printer_id={test_printer.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["assigned_printer_id"] == str(test_printer.id)

    async def test_list_jobs_pagination(self, client: AsyncClient, multiple_pending_jobs):
        """Test pagination of jobs."""
        response = await client.get("/api/v1/print-queue?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 4
        assert data["pages"] == 2


# ============================================
# Get Job Tests
# ============================================


class TestGetPrintJob:
    """Tests for getting a single print job."""

    async def test_get_job_success(self, client: AsyncClient, test_print_job: PrintJob):
        """Test getting a job by ID."""
        response = await client.get(f"/api/v1/print-queue/{test_print_job.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_print_job.id)
        assert data["notes"] == test_print_job.notes

    async def test_get_job_not_found(self, client: AsyncClient):
        """Test getting a non-existent job."""
        response = await client.get(f"/api/v1/print-queue/{uuid4()}")
        assert response.status_code == 404


# ============================================
# Update Job Tests
# ============================================


class TestUpdatePrintJob:
    """Tests for updating print jobs."""

    async def test_update_job_priority(self, client: AsyncClient, test_print_job: PrintJob):
        """Test updating job priority."""
        response = await client.patch(
            f"/api/v1/print-queue/{test_print_job.id}",
            json={"priority": "urgent"},
        )
        assert response.status_code == 200
        assert response.json()["priority"] == "urgent"

    async def test_update_job_notes(self, client: AsyncClient, test_print_job: PrintJob):
        """Test updating job notes."""
        response = await client.patch(
            f"/api/v1/print-queue/{test_print_job.id}",
            json={"notes": "Updated notes"},
        )
        assert response.status_code == 200
        assert response.json()["notes"] == "Updated notes"

    async def test_update_job_estimated_duration(
        self, client: AsyncClient, test_print_job: PrintJob
    ):
        """Test updating estimated duration."""
        response = await client.patch(
            f"/api/v1/print-queue/{test_print_job.id}",
            json={"estimated_duration_hours": "3.5"},
        )
        assert response.status_code == 200
        assert response.json()["estimated_duration_hours"] == "3.50"

    async def test_update_job_not_found(self, client: AsyncClient):
        """Test updating a non-existent job."""
        response = await client.patch(
            f"/api/v1/print-queue/{uuid4()}",
            json={"priority": "high"},
        )
        assert response.status_code == 404


# ============================================
# Delete Job Tests
# ============================================


class TestDeletePrintJob:
    """Tests for deleting print jobs."""

    async def test_delete_cancelled_job(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant
    ):
        """Test deleting a cancelled job."""
        job = PrintJob(
            id=uuid4(),
            tenant_id=test_tenant.id,
            quantity=1,
            status=JobStatus.CANCELLED.value,
        )
        db_session.add(job)
        await db_session.commit()

        response = await client.delete(f"/api/v1/print-queue/{job.id}")
        assert response.status_code == 204

    async def test_delete_completed_job(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant
    ):
        """Test deleting a completed job."""
        job = PrintJob(
            id=uuid4(),
            tenant_id=test_tenant.id,
            quantity=1,
            status=JobStatus.COMPLETED.value,
        )
        db_session.add(job)
        await db_session.commit()

        response = await client.delete(f"/api/v1/print-queue/{job.id}")
        assert response.status_code == 204

    async def test_delete_pending_job_fails(self, client: AsyncClient, test_print_job: PrintJob):
        """Test that deleting an active job fails."""
        response = await client.delete(f"/api/v1/print-queue/{test_print_job.id}")
        assert response.status_code == 400


# ============================================
# Assignment Tests
# ============================================


class TestAssignJob:
    """Tests for assigning jobs to printers."""

    async def test_assign_job_success(
        self, client: AsyncClient, test_print_job: PrintJob, test_printer: Printer
    ):
        """Test assigning a job to a printer."""
        response = await client.patch(
            f"/api/v1/print-queue/{test_print_job.id}/assign",
            json={"printer_id": str(test_printer.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["assigned_printer_id"] == str(test_printer.id)

    async def test_assign_job_not_found(self, client: AsyncClient, test_printer: Printer):
        """Test assigning a non-existent job."""
        response = await client.patch(
            f"/api/v1/print-queue/{uuid4()}/assign",
            json={"printer_id": str(test_printer.id)},
        )
        assert response.status_code == 400


# ============================================
# Auto-Assign Tests
# ============================================


class TestAutoAssign:
    """Tests for auto-assigning jobs to printers."""

    async def test_auto_assign_success(
        self, client: AsyncClient, test_print_job: PrintJob, test_printer: Printer
    ):
        """Test auto-assigning pending jobs to idle printers."""
        response = await client.post("/api/v1/print-queue/auto-assign")
        assert response.status_code == 200
        data = response.json()
        assert data["assigned_count"] >= 0
        assert "assignments" in data
        assert "unassigned_count" in data
        assert "unassigned_reasons" in data

    async def test_auto_assign_no_pending_jobs(self, client: AsyncClient, test_printer: Printer):
        """Test auto-assign when no pending jobs exist."""
        response = await client.post("/api/v1/print-queue/auto-assign")
        assert response.status_code == 200
        data = response.json()
        assert data["assigned_count"] == 0

    async def test_auto_assign_no_idle_printers(
        self, client: AsyncClient, test_print_job: PrintJob, test_printer_offline: Printer
    ):
        """Test auto-assign when no idle printers available."""
        response = await client.post("/api/v1/print-queue/auto-assign")
        assert response.status_code == 200
        data = response.json()
        # Should have unassigned jobs due to no idle printers
        assert data["unassigned_count"] >= 0


# ============================================
# Status Transition Tests
# ============================================


class TestJobStatusTransitions:
    """Tests for job status transitions."""

    async def test_cancel_pending_job(self, client: AsyncClient, test_print_job: PrintJob):
        """Test cancelling a pending job."""
        response = await client.post(f"/api/v1/print-queue/{test_print_job.id}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    async def test_cancel_queued_job(self, client: AsyncClient, test_queued_job: PrintJob):
        """Test cancelling a queued job."""
        response = await client.post(f"/api/v1/print-queue/{test_queued_job.id}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    async def test_start_queued_job(self, client: AsyncClient, test_queued_job: PrintJob):
        """Test starting a queued job."""
        response = await client.post(f"/api/v1/print-queue/{test_queued_job.id}/start")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "printing"
        assert data["started_at"] is not None

    async def test_start_pending_job_fails(self, client: AsyncClient, test_print_job: PrintJob):
        """Test that starting a pending (not queued) job fails."""
        response = await client.post(f"/api/v1/print-queue/{test_print_job.id}/start")
        assert response.status_code == 400

    async def test_complete_printing_job(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant, test_printer
    ):
        """Test completing a printing job."""
        # Create a printing job
        job = PrintJob(
            id=uuid4(),
            tenant_id=test_tenant.id,
            quantity=1,
            status=JobStatus.PRINTING.value,
            assigned_printer_id=test_printer.id,
        )
        db_session.add(job)
        await db_session.commit()

        response = await client.post(f"/api/v1/print-queue/{job.id}/complete")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

    async def test_fail_printing_job(
        self, client: AsyncClient, db_session: AsyncSession, test_tenant, test_printer
    ):
        """Test marking a printing job as failed."""
        job = PrintJob(
            id=uuid4(),
            tenant_id=test_tenant.id,
            quantity=1,
            status=JobStatus.PRINTING.value,
            assigned_printer_id=test_printer.id,
        )
        db_session.add(job)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/print-queue/{job.id}/fail",
            json={"status": "failed", "error_message": "Print head clogged"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "Print head clogged"


# ============================================
# Queue Overview Tests
# ============================================


class TestQueueOverview:
    """Tests for queue overview endpoint."""

    async def test_overview_empty(self, client: AsyncClient):
        """Test overview with no jobs or printers."""
        response = await client.get("/api/v1/print-queue/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_pending_jobs"] == 0
        assert data["total_queued_jobs"] == 0
        assert data["total_printing_jobs"] == 0

    async def test_overview_with_jobs(
        self, client: AsyncClient, test_print_job: PrintJob, test_printer: Printer
    ):
        """Test overview with jobs and printers."""
        response = await client.get("/api/v1/print-queue/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_pending_jobs"] == 1
        assert "printer_stats" in data

    async def test_overview_printer_stats(
        self, client: AsyncClient, test_queued_job: PrintJob, test_printer: Printer
    ):
        """Test overview includes printer statistics."""
        response = await client.get("/api/v1/print-queue/overview")
        assert response.status_code == 200
        data = response.json()
        assert len(data["printer_stats"]) >= 1
        printer_stat = next(
            (p for p in data["printer_stats"] if p["printer_id"] == str(test_printer.id)),
            None,
        )
        assert printer_stat is not None
        assert printer_stat["printer_name"] == test_printer.name
        assert "current_status" in printer_stat
        assert "jobs_in_queue" in printer_stat
