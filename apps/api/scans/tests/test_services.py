"""Tests for ScanTargetService and ScanService."""
import pytest
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.django_db


@pytest.fixture
def workspace(db, user):
    from users.models import Workspace
    return Workspace.objects.create(owner=user, name="WS")


@pytest.fixture
def target(db, user, workspace):
    from scans.services import ScanTargetService
    return ScanTargetService.create(
        user=user, workspace=workspace,
        name="Example", host="example.com",
    )


class TestScanTargetService:
    def test_create_target(self, target):
        assert target.host == "example.com"

    def test_create_duplicate_raises(self, user, workspace, target):
        from scans.services import ScanTargetService
        from core.exceptions import ConflictError
        with pytest.raises(ConflictError):
            ScanTargetService.create(
                user=user, workspace=workspace,
                name="Duplicate", host="example.com",
            )

    def test_get_or_404_unknown_raises(self, user):
        from scans.services import ScanTargetService
        from core.exceptions import NotFoundError
        import uuid
        with pytest.raises(NotFoundError):
            ScanTargetService.get_or_404(user, uuid.uuid4())

    def test_list_for_user(self, user, target):
        from scans.services import ScanTargetService
        targets = ScanTargetService.list_for_user(user)
        assert targets.count() == 1

    def test_delete(self, user, target):
        from scans.services import ScanTargetService
        ScanTargetService.delete(user, target.id)
        assert ScanTargetService.list_for_user(user).count() == 0


class TestScanService:
    def test_create_scan(self, user, target):
        from scans.services import ScanService
        scan = ScanService.create(
            user=user, target_id=target.id,
            plugin_ids=["port_scan"], config={},
        )
        assert scan.status == "pending"
        assert scan.plugin_ids == ["port_scan"]

    def test_create_unknown_plugin_raises(self, user, target):
        from scans.services import ScanService
        from core.exceptions import ServiceError
        with pytest.raises(ServiceError, match="Unknown plugin"):
            ScanService.create(
                user=user, target_id=target.id,
                plugin_ids=["nonexistent_plugin"], config={},
            )

    def test_trigger_queues_celery_task(self, user, target):
        from scans.services import ScanService
        scan = ScanService.create(
            user=user, target_id=target.id,
            plugin_ids=["port_scan"], config={},
        )
        with patch("scans.tasks.run_scan.delay") as mock_delay:
            triggered = ScanService.trigger(user, scan.id)
        assert triggered.status == "queued"
        mock_delay.assert_called_once_with(str(scan.id))

    def test_trigger_non_pending_raises(self, user, target):
        from scans.services import ScanService
        from core.exceptions import ServiceError
        scan = ScanService.create(
            user=user, target_id=target.id,
            plugin_ids=["ssl_check"], config={},
        )
        scan.status = "completed"
        scan.save(update_fields=["status"])
        with pytest.raises(ServiceError, match="Cannot start"):
            ScanService.trigger(user, scan.id)

    def test_cancel_pending(self, user, target):
        from scans.services import ScanService
        scan = ScanService.create(
            user=user, target_id=target.id,
            plugin_ids=["port_scan"], config={},
        )
        cancelled = ScanService.cancel(user, scan.id)
        assert cancelled.status == "cancelled"
