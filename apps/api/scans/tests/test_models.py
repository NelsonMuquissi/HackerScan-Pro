"""Tests for scans models: status machine, finding counts, fingerprinting."""
import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db


# ─── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def workspace(db, user):
    from users.models import Workspace
    return Workspace.objects.create(owner=user, name="Test Workspace")


@pytest.fixture
def target(db, user, workspace):
    from scans.models import ScanTarget
    return ScanTarget.objects.create(
        owner=user, workspace=workspace,
        name="Example", host="example.com", target_type="domain",
    )


@pytest.fixture
def pending_scan(db, user, target):
    from scans.models import Scan
    return Scan.objects.create(
        target=target, triggered_by=user,
        plugin_ids=["port_scan", "ssl_check"],
    )


# ─── ScanTarget ─────────────────────────────────────────────────────────────

class TestScanTarget:
    def test_create(self, target):
        assert target.host == "example.com"
        assert target.target_type == "domain"
        assert str(target) == "Example (example.com)"

    def test_unique_per_workspace(self, db, user, workspace):
        from scans.models import ScanTarget
        from django.db import IntegrityError
        ScanTarget.objects.create(
            owner=user, workspace=workspace, name="A", host="dup.com"
        )
        with pytest.raises(IntegrityError):
            ScanTarget.objects.create(
                owner=user, workspace=workspace, name="B", host="dup.com"
            )


# ─── Scan status machine ─────────────────────────────────────────────────────

class TestScanStatusMachine:
    def test_initial_status_pending(self, pending_scan):
        assert pending_scan.status == "pending"

    def test_mark_running(self, pending_scan):
        pending_scan.mark_running()
        pending_scan.refresh_from_db()
        assert pending_scan.status == "running"
        assert pending_scan.started_at is not None

    def test_mark_completed(self, pending_scan):
        pending_scan.mark_running()
        pending_scan.mark_completed()
        pending_scan.refresh_from_db()
        assert pending_scan.status == "completed"
        assert pending_scan.finished_at is not None

    def test_mark_failed(self, pending_scan):
        pending_scan.mark_failed("Connection refused")
        pending_scan.refresh_from_db()
        assert pending_scan.status == "failed"
        assert "Connection refused" in pending_scan.error_message

    def test_duration_seconds(self, pending_scan):
        pending_scan.mark_running()
        pending_scan.mark_completed()
        assert isinstance(pending_scan.duration_seconds, float)
        assert pending_scan.duration_seconds >= 0


# ─── Finding ─────────────────────────────────────────────────────────────────

class TestFinding:
    def test_fingerprint_auto_generated(self, db, pending_scan):
        from scans.models import Finding
        f = Finding.objects.create(
            scan=pending_scan, plugin_slug="port_scan",
            severity="high", title="Open port 22/SSH",
            description="Port 22 is open.",
        )
        assert len(f.fingerprint) == 64

    def test_finding_counts_updated_on_complete(self, db, pending_scan):
        from scans.models import Finding
        for severity in ["critical", "high", "medium", "info"]:
            Finding.objects.create(
                scan=pending_scan, plugin_slug="test",
                severity=severity, title=f"Test {severity}",
                description="desc",
            )
        pending_scan.mark_running()
        pending_scan.mark_completed()
        pending_scan.refresh_from_db()
        assert pending_scan.total_findings == 4
        assert pending_scan.critical_count == 1
        assert pending_scan.high_count == 1
