"""Tests for the scans REST API views."""
import pytest
from unittest.mock import patch
import uuid

pytestmark = pytest.mark.django_db


@pytest.fixture
def workspace(db, user):
    from users.models import Workspace
    return Workspace.objects.create(owner=user, name="WS")


@pytest.fixture
def target(db, user, workspace):
    from scans.models import ScanTarget
    return ScanTarget.objects.create(
        owner=user, workspace=workspace, name="Example", host="example.com"
    )


@pytest.fixture
def scan(db, user, target):
    from scans.models import Scan
    return Scan.objects.create(
        target=target, triggered_by=user, plugin_ids=["port_scan"]
    )


# ─── Targets ─────────────────────────────────────────────────────────────────

class TestScanTargetListCreate:
    URL = "/v1/scans/targets/"

    def test_requires_auth(self, api_client):
        r = api_client.get(self.URL)
        assert r.status_code == 401

    def test_list_empty(self, auth_client):
        r = auth_client.get(self.URL)
        assert r.status_code == 200
        assert r.data == []

    def test_create_target(self, auth_client):
        r = auth_client.post(self.URL, {"name": "Test", "host": "test.com"}, format="json")
        assert r.status_code == 201
        assert r.data["host"] == "test.com"

    def test_create_duplicate_target(self, auth_client, target):
        r = auth_client.post(self.URL, {"name": "Dup", "host": "example.com"}, format="json")
        assert r.status_code == 409


class TestScanTargetDetail:
    def url(self, tid): return f"/v1/scans/targets/{tid}/"

    def test_get(self, auth_client, target):
        r = auth_client.get(self.url(target.id))
        assert r.status_code == 200
        assert r.data["host"] == "example.com"

    def test_patch(self, auth_client, target):
        r = auth_client.patch(self.url(target.id), {"description": "updated"}, format="json")
        assert r.status_code == 200

    def test_delete(self, auth_client, target):
        r = auth_client.delete(self.url(target.id))
        assert r.status_code == 204

    def test_not_found(self, auth_client):
        r = auth_client.get(self.url(uuid.uuid4()))
        assert r.status_code == 404


# ─── Scans ───────────────────────────────────────────────────────────────────

class TestScanListCreate:
    URL = "/v1/scans/"

    def test_list(self, auth_client, scan):
        r = auth_client.get(self.URL)
        assert r.status_code == 200
        assert len(r.data) == 1

    def test_create(self, auth_client, target):
        r = auth_client.post(self.URL, {
            "target_id": str(target.id),
            "plugin_ids": ["port_scan"],
        }, format="json")
        assert r.status_code == 201
        assert r.data["status"] == "pending"


class TestScanDetail:
    def url(self, sid): return f"/v1/scans/{sid}/"

    def test_get(self, auth_client, scan):
        r = auth_client.get(self.url(scan.id))
        assert r.status_code == 200
        assert r.data["id"] == str(scan.id)


class TestScanStart:
    def test_start_queues_task(self, auth_client, scan):
        with patch("scans.tasks.run_scan.delay") as mock_delay:
            r = auth_client.post(f"/v1/scans/{scan.id}/start/")
        assert r.status_code == 200
        assert r.data["status"] == "queued"
        mock_delay.assert_called_once()


class TestScanCancel:
    def test_cancel(self, auth_client, scan):
        r = auth_client.post(f"/v1/scans/{scan.id}/cancel/")
        assert r.status_code == 200
        assert r.data["status"] == "cancelled"


class TestScanFindings:
    def test_empty_findings(self, auth_client, scan):
        r = auth_client.get(f"/v1/scans/{scan.id}/findings/")
        assert r.status_code == 200
        assert r.data == []

    def test_findings_with_data(self, auth_client, scan):
        from scans.models import Finding
        Finding.objects.create(
            scan=scan, plugin_slug="port_scan",
            severity="high", title="Open 22", description="SSH open",
        )
        r = auth_client.get(f"/v1/scans/{scan.id}/findings/")
        assert len(r.data) == 1
        assert r.data[0]["severity"] == "high"

    def test_findings_severity_filter(self, auth_client, scan):
        from scans.models import Finding
        Finding.objects.create(scan=scan, plugin_slug="x", severity="info",  title="I", description="d")
        Finding.objects.create(scan=scan, plugin_slug="x", severity="critical", title="C", description="d")
        r = auth_client.get(f"/v1/scans/{scan.id}/findings/?severity=critical")
        assert len(r.data) == 1
        assert r.data[0]["severity"] == "critical"
