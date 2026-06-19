"""
Business logic for the scans app.
Views delegate all state changes and queries here.
"""
import logging
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import transaction

from core.exceptions import ConflictError, NotFoundError, ServiceError
from .models import Scan, ScanStatus, ScanTarget, Finding, FindingStatus
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from billing.services import BillingService

logger = logging.getLogger(__name__)
User   = get_user_model()


def _dispatch_task(celery_task, *args, **kwargs):
    """
    Dispatch a Celery task with automatic fallback.
    If Celery/Redis is unavailable, run the task in a background thread.
    This ensures scans never get stuck in QUEUED status.
    """
    import threading

    try:
        # Test broker connectivity first
        from celery import current_app
        conn = current_app.connection()
        conn.ensure_connection(max_retries=1, timeout=2)
        conn.close()
        # Broker is reachable — dispatch normally
        celery_task.delay(*args, **kwargs)
        logger.info("_dispatch_task: dispatched %s via Celery", celery_task.name)
    except Exception as e:
        logger.warning(
            "_dispatch_task: Celery/Redis unavailable (%s). "
            "Running %s in background thread.",
            e, celery_task.name
        )
        # Fallback: run in a daemon thread
        def _run_in_thread():
            try:
                import django
                django.setup()
                celery_task(*args, **kwargs)
            except Exception as exc:
                logger.error("_dispatch_task thread error for %s: %s", celery_task.name, exc)

        t = threading.Thread(target=_run_in_thread, daemon=True)
        t.start()

import asyncio

async def async_broadcast_scan_update(scan: Scan):
    """Async version of scan update broadcast."""
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
    await channel_layer.group_send(group_name, payload)

def broadcast_scan_update(scan: Scan):
    """Broadcast scan status to the workspace websocket group. Async-aware."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(async_broadcast_scan_update(scan))
    except RuntimeError:
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

async def async_broadcast_terminal_line(scan: Scan, line: str):
    """Async version of terminal line broadcast."""
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    group_name = f"scan_{scan.id}"
    payload = {
        "type": "scan_terminal_line",
        "data": line
    }
    await channel_layer.group_send(group_name, payload)

def broadcast_terminal_line(scan: Scan, line: str):
    """Broadcast a single terminal line to the scan-specific websocket group. Async-aware."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(async_broadcast_terminal_line(scan, line))
    except RuntimeError:
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
        """
        Creates a new ScanTarget within a workspace.
        Note: The 'owner' field is kept for historical tracking but isolation
        is strictly enforced via the 'workspace' foreign key.
        """
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
    def create(user, workspace_id: UUID, *, target_id: UUID, scan_type: str, 
               config: dict, plugin_ids: list[str] | None = None) -> Scan:
        # Validate target exists in this workspace
        target = ScanTargetService.get_or_404(workspace_id, target_id)

        # Validate scan_type
        if scan_type not in ScanType.values:
            raise ServiceError(f"Unknown scan type: {scan_type}. "
                                f"Available: {', '.join(ScanType.values)}")

        # Validate plugin_ids
        if plugin_ids:
            from scans.strategies.base import list_strategies
            valid_slugs = {s.slug for s in list_strategies()}
            valid_slugs.update(["port_scan", "ssl_check", "headers_check"])
            for p in plugin_ids:
                if p not in valid_slugs:
                    raise ServiceError(f"Unknown plugin: {p}")


        scan = Scan.objects.create(
            target=target,
            triggered_by=user,
            scan_type=scan_type,
            plugin_ids=plugin_ids or [],
            config=config,
            status=ScanStatus.PENDING,
        )
        
        # Increment usage counter
        BillingService.increment_usage(target.workspace, "scans_count")
        
        from users.models import AuditLog
        AuditLog.log(
            user=user,
            action="scan.create",
            workspace=target.workspace,
            resource_id=scan.id,
            resource_type="scan",
            metadata={
                "target_host": target.host,
                "scan_type": scan_type,
                "config": config
            }
        )

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

        _dispatch_task(run_scan, str(scan.id))
        logger.info("ScanService.trigger: queued scan %s", scan.id)

        from users.models import AuditLog
        AuditLog.log(
            user=scan.triggered_by,
            action="scan.trigger",
            workspace=scan.target.workspace,
            resource_id=scan.id,
            resource_type="scan",
            metadata={"target_host": scan.target.host}
        )

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

        from users.models import AuditLog
        AuditLog.log(
            user=None, # System action or user context if available
            action="scan.cancel",
            workspace=scan.target.workspace,
            resource_id=scan.id,
            resource_type="scan",
            metadata={"target_host": scan.target.host}
        )

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
    def quick_scan(user, target_url: str, scan_type: str = ScanType.QUICK,
                   workspace_id: UUID | None = None, plugin_ids: list[str] | None = None) -> Scan:
        """
        One-step convenience: parse URL → upsert ScanTarget → create Scan → trigger.
        Used by the dashboard's quick-scan form.
        """
        from urllib.parse import urlparse  # noqa: PLC0415
        from .tasks import run_scan        # noqa: PLC0415
        from users.models import Workspace, WorkspaceMember # noqa: PLC0415

        parsed = urlparse(target_url)
        # Handle cases like 'google.com' (no scheme) vs 'https://google.com'
        host = parsed.hostname or parsed.path.split("/")[0]
        if not host:
            raise ServiceError("Could not extract a hostname from the provided URL.")

        # 1. Resolve Workspace
        workspace = None
        if workspace_id:
            try:
                workspace = Workspace.objects.get(pk=workspace_id)
            except Workspace.DoesNotExist:
                raise NotFoundError("Specified workspace not found.")
        else:
            # Fallback for legacy calls or missing ID
            owned = user.owned_workspaces.first()
            if owned:
                workspace = owned
            else:
                membership = user.memberships.select_related("workspace").first()
                if membership:
                    workspace = membership.workspace

        if workspace is None:
            # Auto-create workspace on first scan (bootstrap personal workspace)
            workspace = Workspace.objects.create(
                owner=user,
                name=f"{user.full_name or user.email}'s Workspace",
                slug=f"personal-{user.id}",
            )
            WorkspaceMember.objects.create(
                workspace=workspace, user=user, role="owner"
            )

        # 2. Enforce Quota
        allowed, reason = BillingService.check_quota(workspace, "create_scan", user=user)
        if not allowed:
            raise ServiceError(reason)

        # 3. Create/Retrieve Target & Scan
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
                plugin_ids=plugin_ids or [],
                config={},
                status=ScanStatus.QUEUED,
            )
            
            # Increment usage counter
            BillingService.increment_usage(workspace, "scans_count")

        _dispatch_task(run_scan, str(scan.id))
        logger.info("ScanService.quick_scan: queued scan %s for %s in workspace %s", scan.id, host, workspace.id)

        from users.models import AuditLog
        AuditLog.log(
            "scan.quick_create",
            user=user,
            workspace=workspace,
            resource_id=scan.id,
            resource_type="scan",
            metadata={"target_host": host, "scan_type": scan_type}
        )

        return scan

    @staticmethod
    def rescan(workspace_id: UUID, scan_id: UUID, user) -> Scan:
        """
        Create a new scan based on an existing scan's configuration and queue it.
        """
        old_scan = ScanService.get_or_404(workspace_id, scan_id)
        
        # Enforce Quota for the new scan
        allowed, reason = BillingService.check_quota(old_scan.target.workspace, "create_scan", user=user)
        if not allowed:
            raise ServiceError(reason)

        with transaction.atomic():
            new_scan = Scan.objects.create(
                target=old_scan.target,
                triggered_by=user,
                scan_type=old_scan.scan_type,
                plugin_ids=old_scan.plugin_ids,
                config=old_scan.config,
                status=ScanStatus.QUEUED,
            )
            
            # Increment usage counter
            BillingService.increment_usage(old_scan.target.workspace, "scans_count")

        from .tasks import run_scan
        _dispatch_task(run_scan, str(new_scan.id))
        logger.info("ScanService.rescan: cloned scan %s into %s and queued", scan_id, new_scan.id)

        from users.models import AuditLog
        AuditLog.log(
            user=user,
            action="scan.rescan",
            workspace=old_scan.target.workspace,
            resource_id=new_scan.id,
            resource_type="scan",
            metadata={
                "original_scan_id": str(scan_id),
                "target_host": old_scan.target.host,
                "scan_type": old_scan.scan_type
            }
        )

        return new_scan

    @staticmethod
    def assess_risk(workspace_id: UUID, scan_id: UUID) -> dict:
        """
        Assess the global ML risk for the scan and update the Scan and ScanTarget models.
        """
        scan = ScanService.get_or_404(workspace_id, scan_id)
        
        # We only assess if there are findings
        findings_qs = scan.findings.all()
        if not findings_qs.exists():
            return {"score": 0.0, "classification": "Low", "reasoning": "Nenhuma vulnerabilidade encontrada."}
            
        findings_data = [
            {
                "title": f.title,
                "severity": f.severity,
                "cvss_score": f.cvss_score,
                "epss_score": f.epss_score
            }
            for f in findings_qs
        ]
        
        try:
            from ai.services import ai_service
            analysis, usage = ai_service.assess_target_risk(scan.target.host, findings_data)
            
            # Update Scan
            scan.ml_risk_score = analysis.get("score", 0.0)
            scan.ml_risk_classification = analysis.get("classification", "Unknown")
            scan.save(update_fields=["ml_risk_score", "ml_risk_classification"])
            
            # Update Target
            scan.target.ml_risk_score = scan.ml_risk_score
            scan.target.ml_risk_classification = scan.ml_risk_classification
            scan.target.save(update_fields=["ml_risk_score", "ml_risk_classification"])
            
            return analysis
        except Exception as e:
            logger.error("Failed to assess risk via AI for scan %s: %s", scan.id, e)
            raise ServiceError("Risk assessment failed.")

# ─── FindingService ───────────────────────────────────────────────────────

from .models import Finding, FindingStatus

class FindingService:
    @staticmethod
    def get_or_404(workspace_id: UUID, finding_id: UUID) -> Finding:
        try:
            return Finding.objects.select_related("scan__target").get(
                pk=finding_id, scan__target__workspace_id=workspace_id
            )
        except Finding.DoesNotExist:
            raise NotFoundError("Finding not found.")

    @staticmethod
    def verify(workspace_id: UUID, finding_id: UUID) -> Finding:
        """Trigger an automated verification for a finding."""
        finding = FindingService.get_or_404(workspace_id, finding_id)
        
        from .tasks import verify_finding_task  # noqa: PLC0415
        _dispatch_task(verify_finding_task, str(finding.id))
        
        logger.info("FindingService.verify: queued verification for finding %s", finding.id)
        return finding

    @staticmethod
    def verify_all(workspace_id: UUID, scan_id: UUID) -> dict:
        """Batch-verify all active findings for a completed scan."""
        scan = ScanService.get_or_404(workspace_id, scan_id)
        
        from .tasks import verify_all_findings_task  # noqa: PLC0415
        _dispatch_task(verify_all_findings_task, str(scan.id))
        
        active_count = Finding.objects.filter(
            scan=scan, status=FindingStatus.ACTIVE
        ).count()
        
        logger.info("FindingService.verify_all: queued batch verification for scan %s (%d findings)", scan.id, active_count)
        return {"queued": active_count, "scan_id": str(scan.id)}

    @staticmethod
    def generate_poc(workspace_id: UUID, finding_id: UUID) -> str:
        """Use AI to generate a professional POC for the finding."""
        finding = FindingService.get_or_404(workspace_id, finding_id)
        
        if finding.poc and not finding.poc.startswith("AI-GEN"):
            return finding.poc

        try:
            from ai.services import ai_service
            poc = ai_service.generate_vulnerability_poc(
                title=finding.title,
                description=finding.description,
                evidence=finding.evidence,
                request_data=finding.request
            )
            finding.poc = poc
            finding.save(update_fields=["poc"])
            return poc
        except Exception as e:
            logger.error("Failed to generate POC via AI: %s", e)
            return "POC generation failed. Please try again later."

    @staticmethod
    def analyze_false_positive(workspace_id: UUID, finding_id: UUID) -> dict:
        """Use AI to analyze if a finding is a false positive and update it."""
        from django.utils import timezone  # noqa: PLC0415
        
        finding = FindingService.get_or_404(workspace_id, finding_id)
        
        # 1. Fetch History for learning
        history_qs = Finding.objects.filter(
            scan__target__workspace_id=workspace_id,
            is_false_positive=True
        ).exclude(id=finding_id).order_by("-created_at")[:5]
        
        history_data = [
            {"title": h.title, "reason": h.ai_reasoning or "Marcado manualmente"}
            for h in history_qs
        ]
        
        try:
            from ai.services import ai_service
            analysis = ai_service.analyze_false_positive(
                finding_title=finding.title,
                description=finding.description,
                evidence=finding.evidence,
                history=history_data
            )
            
            result, usage = analysis
            
            is_fp = result.get("is_false_positive", False)
            confidence = result.get("confidence", 0.0)
            reasoning = result.get("reasoning", "")
            
            finding.is_false_positive = is_fp
            finding.ai_confidence = confidence if not is_fp else (1.0 - confidence)
            finding.ai_reasoning = reasoning
            
            from django.conf import settings  # noqa: PLC0415
            if is_fp and confidence > settings.AI_FP_SUPPRESSION_THRESHOLD:
                finding.status = FindingStatus.SUPPRESSED
                finding.resolved_at = timezone.now()
            
            finding.save(update_fields=["is_false_positive", "ai_confidence", "ai_reasoning", "status", "resolved_at"])
            return result
        except Exception as e:
            logger.error("Failed to analyze false positive via AI: %s", e)
            raise ServiceError("False positive analysis failed. Please try again later.")

    @staticmethod
    def submit_feedback(workspace_id: UUID, finding_id: UUID, feedback: str) -> Finding:
        """Submit manual feedback for a finding's AI analysis."""
        from django.utils import timezone  # noqa: PLC0415
        
        finding = FindingService.get_or_404(workspace_id, finding_id)
        
        if feedback == "confirmed_valid":
            finding.user_verification = "confirmed_valid"
            finding.is_false_positive = False
            # If it was suppressed, reopen it
            if finding.status == FindingStatus.SUPPRESSED:
                finding.status = FindingStatus.ACTIVE
                finding.resolved_at = None
        elif feedback == "confirmed_fp":
            finding.user_verification = "confirmed_fp"
            finding.is_false_positive = True
            finding.status = FindingStatus.SUPPRESSED
            finding.resolved_at = timezone.now()
        else:
            raise ServiceError(f"Invalid feedback type: {feedback}")
            
        finding.save(update_fields=["user_verification", "is_false_positive", "status", "resolved_at"])
        return finding
