"""
Business logic for the scans app.
Views delegate all state changes and queries here.
"""
import logging
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import transaction

from core.exceptions import ConflictError, NotFoundError, ServiceError
from .models import Scan, ScanStatus, ScanTarget
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from billing.services import BillingService

logger = logging.getLogger(__name__)
User   = get_user_model()

def broadcast_scan_update(scan: Scan):
    """Broadcast scan status to the workspace websocket group."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    group_name = f"workspace_{scan.target.workspace_id}"
    payload = {
        "type": "scan_update",
        "payload": {
            "scan_id": str(scan.id),
            "status": scan.status,
            "target": scan.target.host,
            "total_findings": scan.total_findings,
        }
    }
    async_to_sync(channel_layer.group_send)(group_name, payload)

def broadcast_terminal_line(scan: Scan, line: str):
    """Broadcast a single terminal line to the scan-specific websocket group."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    group_name = f"scan_{scan.id}"
    payload = {
        "type": "scan_terminal_line",
        "data": line
    }
    async_to_sync(channel_layer.group_send)(group_name, payload)

# Lazily imported to avoid circular imports at module load
AVAILABLE_PLUGINS = ["port_scan", "ssl_check", "headers_check"]


# ─── ScanTargetService ────────────────────────────────────────────────────

class ScanTargetService:
    @staticmethod
    def create(user, workspace, *, name: str, host: str, target_type: str = "domain",
               description: str = "", tags: list | None = None) -> ScanTarget:
        if ScanTarget.objects.filter(workspace=workspace, host=host).exists():
            raise ConflictError(f"A target with host '{host}' already exists in this workspace.")
        return ScanTarget.objects.create(
            workspace=workspace, owner=user, name=name, host=host,
            target_type=target_type, description=description, tags=tags or [],
        )

    @staticmethod
    def list_for_workspace(workspace_id: UUID) -> "QuerySet[ScanTarget]":
        return ScanTarget.objects.filter(workspace_id=workspace_id).order_by("-created_at")

    @staticmethod
    def get_or_404(workspace_id: UUID, target_id: UUID) -> ScanTarget:
        try:
            return ScanTarget.objects.get(pk=target_id, workspace_id=workspace_id)
        except ScanTarget.DoesNotExist:
            raise NotFoundError("Scan target not found.")

    @staticmethod
    def delete(workspace_id: UUID, target_id: UUID) -> None:
        target = ScanTargetService.get_or_404(workspace_id, target_id)
        target.delete()


from .models import Scan, ScanStatus, ScanTarget, ScanType

class ScanService:
    @staticmethod
    def create(user, workspace_id: UUID, *, target_id: UUID, scan_type: str, config: dict) -> Scan:
        # Validate target exists in this workspace
        target = ScanTargetService.get_or_404(workspace_id, target_id)

        # Validate scan_type
        if scan_type not in ScanType.values:
            raise ServiceError(f"Unknown scan type: {scan_type}. "
                                f"Available: {', '.join(ScanType.values)}")

        scan = Scan.objects.create(
            target=target,
            triggered_by=user,
            scan_type=scan_type,
            config=config,
            status=ScanStatus.PENDING,
        )
        
        # Increment usage counter
        BillingService.increment_usage(target.workspace, "scans_count")
        
        return scan

    @staticmethod
    def trigger(workspace_id: UUID, scan_id: UUID) -> Scan:
        """Queue the scan for async execution via Celery."""
        from .tasks import run_scan  # noqa: PLC0415 — avoids circular

        scan = ScanService.get_or_404(workspace_id, scan_id)
        if scan.status not in (ScanStatus.PENDING,):
            raise ServiceError(
                f"Cannot start a scan in status '{scan.status}'. "
                "Only pending scans can be queued."
            )
        scan.status = ScanStatus.QUEUED
        scan.save(update_fields=["status"])

        run_scan.delay(str(scan.id))
        logger.info("ScanService.trigger: queued scan %s via Celery", scan.id)
        return scan

    @staticmethod
    def cancel(workspace_id: UUID, scan_id: UUID) -> Scan:
        from celery import current_app           # noqa: PLC0415

        scan = ScanService.get_or_404(workspace_id, scan_id)
        if scan.status not in (ScanStatus.PENDING, ScanStatus.QUEUED, ScanStatus.RUNNING):
            raise ServiceError(f"Cannot cancel a scan in status '{scan.status}'.")

        # Attempt to revoke Celery task (best-effort)
        if scan.celery_task_id:
            try:
                current_app.control.revoke(scan.celery_task_id, terminate=True)
            except Exception:
                pass

        scan.status = ScanStatus.CANCELLED
        scan.save(update_fields=["status"])
        return scan

    @staticmethod
    def list_for_workspace(workspace_id: UUID, target_id: UUID | None = None):
        qs = Scan.objects.filter(target__workspace_id=workspace_id).select_related("target")
        if target_id:
            qs = qs.filter(target_id=target_id)
        return qs.order_by("-created_at")

    @staticmethod
    def get_or_404(workspace_id: UUID, scan_id: UUID) -> Scan:
        try:
            return Scan.objects.select_related("target").get(pk=scan_id, target__workspace_id=workspace_id)
        except Scan.DoesNotExist:
            raise NotFoundError("Scan not found.")

    @staticmethod
    def get_findings(workspace_id: UUID, scan_id: UUID, severity: str | None = None):
        scan = ScanService.get_or_404(workspace_id, scan_id)
        qs   = scan.findings.all()
        if severity:
            qs = qs.filter(severity=severity)
        return qs

    @staticmethod
    def quick_scan(user, target_url: str, scan_type: str = ScanType.QUICK) -> Scan:
        """
        One-step convenience: parse URL → upsert ScanTarget → create Scan → trigger.
        Used by the dashboard's quick-scan form.
        """
        from urllib.parse import urlparse  # noqa: PLC0415
        from .tasks import run_scan        # noqa: PLC0415

        parsed = urlparse(target_url)
        host = parsed.hostname or parsed.path.split("/")[0]
        if not host:
            raise ServiceError("Could not extract a hostname from the provided URL.")

        # Get the user's workspace (first owned workspace, or first membership)
        workspace = None
        owned = user.owned_workspaces.first()
        if owned:
            workspace = owned
        else:
            membership = user.memberships.select_related("workspace").first()
            if membership:
                workspace = membership.workspace

        if workspace is None:
            # Auto-create workspace on first scan (handles legacy users without one)
            from users.models import Workspace, WorkspaceMember  # noqa: PLC0415
            workspace = Workspace.objects.create(
                owner=user,
                name=f"{user.full_name or user.email}'s Workspace",
                slug=f"personal-{user.id}",
            )
            WorkspaceMember.objects.create(
                workspace=workspace, user=user, role="owner"
            )

        # Enforce Quota
        allowed, reason = BillingService.check_quota(workspace, "create_scan")
        if not allowed:
            raise ServiceError(reason)

        with transaction.atomic():
            target, _created = ScanTarget.objects.get_or_create(
                workspace=workspace,
                host=host,
                defaults={
                    "owner": user,
                    "name": host,
                    "target_type": "domain",
                },
            )

            scan = Scan.objects.create(
                target=target,
                triggered_by=user,
                scan_type=scan_type,
                config={},
                status=ScanStatus.QUEUED,
            )
            
            # Increment usage counter
            BillingService.increment_usage(workspace, "scans_count")

        run_scan.delay(str(scan.id))
        logger.info("ScanService.quick_scan: queued scan %s for %s", scan.id, host)
        return scan
