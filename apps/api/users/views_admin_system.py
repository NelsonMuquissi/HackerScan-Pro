from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .views_base import BaseView
from .decorators import superadmin_required
from .models import Workspace, AuditLog
from scans.models import Scan, Finding, ScanTarget, ScanPlugin
from .serializers import AuditLogSerializer
from rest_framework import serializers

User = get_user_model()

# --- Extra Serializers ---

class GlobalAdminWorkspaceSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    
    class Meta:
        model = Workspace
        fields = ["id", "name", "slug", "plan", "owner_email", "is_active", "created_at"]
        read_only_fields = fields

class GlobalAdminScanSerializer(serializers.ModelSerializer):
    target_host = serializers.CharField(source="target.host", read_only=True)
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)
    
    class Meta:
        model = Scan
        fields = [
            "id", "target_host", "workspace_name", "status", "scan_type",
            "total_findings", "critical_count", "high_count", 
            "started_at", "finished_at", "created_at"
        ]
        read_only_fields = fields

class GlobalAdminScanPluginSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanPlugin
        fields = "__all__"

# --- Views ---

@method_decorator(superadmin_required, name='dispatch')
class GlobalAdminWorkspaceListView(BaseView):
    """GET /v1/admin/workspaces/ — List all workspaces platform-wide."""
    def get(self, request):
        workspaces = Workspace.objects.all().order_by("-created_at")
        serializer = GlobalAdminWorkspaceSerializer(workspaces, many=True)
        return self.success_response(serializer.data)

@method_decorator(superadmin_required, name='dispatch')
class GlobalAdminScanListView(BaseView):
    """GET /v1/admin/scans/ — List all scans platform-wide."""
    def get(self, request):
        scans = Scan.objects.all().order_by("-created_at")[:100]  # Limit to last 100 for performance
        serializer = GlobalAdminScanSerializer(scans, many=True)
        return self.success_response(serializer.data)

@method_decorator(superadmin_required, name='dispatch')
class GlobalAdminAuditLogListView(BaseView):
    """GET /v1/admin/audit-logs/ — View all platform audit logs."""
    def get(self, request):
        logs = AuditLog.objects.all().select_related('user', 'workspace').order_by("-created_at")[:200]
        serializer = AuditLogSerializer(logs, many=True)
        return self.success_response(serializer.data)

@method_decorator(superadmin_required, name='dispatch')
class GlobalAdminSystemHealthView(BaseView):
    """GET /v1/admin/system/health/ — Monitor system health."""
    def get(self, request):
        # 1. Database Check
        db_status = "UP"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            db_status = "DOWN"

        # 2. Redis Check (Optional if available)
        redis_status = "UNKNOWN"
        try:
            import redis
            from django.conf import settings
            r = redis.from_url(settings.CACHES['default']['LOCATION'])
            if r.ping():
                redis_status = "UP"
        except Exception:
            redis_status = "DOWN"

        # 3. Celery Check
        celery_status = "UNKNOWN"
        try:
            # This is a simplified check
            from config.celery import app
            insp = app.control.inspect()
            stats = insp.stats()
            if stats:
                celery_status = "UP"
                worker_count = len(stats)
            else:
                celery_status = "DOWN"
                worker_count = 0
        except Exception:
            celery_status = "OFFLINE"
            worker_count = 0

        # 4. Audit Log Integrity Check (Use cache)
        from django.core.cache import cache
        integrity_cache = cache.get("audit_log_integrity_status")
        
        if integrity_cache:
            audit_status = integrity_cache.get("status")
            tampered_count = integrity_cache.get("violation_count", 0)
            total_chained = integrity_cache.get("logs_processed", 0)
            last_check = integrity_cache.get("last_checked")
        else:
            audit_status = "PENDING"
            tampered_count = 0
            total_chained = AuditLog.objects.exclude(current_hash__isnull=True).count()
            last_check = None

        # 5. Audit Repair Progress
        repair_progress = cache.get("audit_repair_progress")

        return self.success_response({
            "status": "HEALTHY" if (db_status == "UP" and audit_status in ["SECURE", "PENDING"]) else "DEGRADED",
            "database": db_status,
            "redis": redis_status,
            "celery": celery_status,
            "audit_integrity": {
                "status": audit_status,
                "tampered_detected": tampered_count,
                "total_chained_logs": total_chained,
                "last_check_at": last_check,
                "repair_progress": repair_progress
            },
            "workers": worker_count,
            "server_time": timezone.now(),
            "environment": "production" if not connection.settings_dict.get('NAME', '').endswith('.sqlite3') else "development"
        })

@method_decorator(superadmin_required, name='dispatch')
class GlobalAdminMaintenanceView(BaseView):
    """POST /v1/admin/system/maintenance/ — Trigger maintenance tasks."""
    def post(self, request):
        action = self.json_body.get("action")
        
        if action == "reset_quotas":
            from billing.models import UsageRecord
            UsageRecord.objects.all().update(scans_count=0)
            return self.success_response({"message": "All workspace quotas reset successfully."})
            
        if action == "repair_findings":
            import hashlib
            from scans.models import FindingStatus
            findings = Finding.objects.all()
            updated = 0
            for f in findings:
                raw = f"{f.scan.target_id}:{f.plugin_slug}:{f.title}"
                f.fingerprint = hashlib.sha256(raw.encode()).hexdigest()[:64]
                f.status = FindingStatus.ACTIVE
                if f.severity:
                    f.severity = f.severity.lower()
                f.save()
                updated += 1
            return self.success_response({"message": f"Successfully repaired {updated} findings."})

        if action == "clear_cache":
            from django.core.cache import cache
            cache.clear()
            return self.success_response({"message": "System cache cleared."})

        if action == "cleanup_scans":
            from scans.models import Scan, ScanStatus
            cutoff = timezone.now() - timezone.timedelta(hours=2)
            stale = Scan.objects.filter(
                status=ScanStatus.RUNNING,
                started_at__lt=cutoff
            )
            count = stale.count()
            stale.update(
                status=ScanStatus.FAILED,
                finished_at=timezone.now(),
                error_message="Marked as failed by admin maintenance (stale running scan)."
            )
            return self.success_response({"message": f"Cleaned up {count} stale scan(s)."})

        if action == "sync_plugins":
            # Import all strategy modules so the registry is populated
            import importlib
            STRATEGY_MODULES = [
                "scans.strategies.port_scan",
                "scans.strategies.ssl_check",
                "scans.strategies.headers_check",
                "scans.strategies.nuclei_scan",
                "scans.strategies.subdomain_recon",
                "scans.strategies.sslyze_audit",
                "scans.strategies.dir_fuzzing",
                "scans.strategies.resource_discovery",
                "scans.strategies.specialized",
                "scans.strategies.sqlmap_scan",
                "scans.strategies.xss_scan",
                "scans.strategies.js_secrets",
                "scans.strategies.dns_audit",
                "scans.strategies.cloud_enum",
                "scans.strategies.container_security",
                "scans.strategies.api_fuzzer",
                "scans.strategies.shodan_recon",
                "scans.strategies.dast_auth",
            ]
            for mod in STRATEGY_MODULES:
                try:
                    importlib.import_module(mod)
                except Exception:
                    pass

            from scans.strategies.base import list_strategies
            created_count = 0
            for strategy in list_strategies():
                _, created = ScanPlugin.objects.get_or_create(
                    slug=strategy.slug,
                    defaults={
                        "name": strategy.name,
                        "description": getattr(strategy, "description", ""),
                        "is_active": True,
                    }
                )
                if created:
                    created_count += 1
            total = ScanPlugin.objects.count()
            return self.success_response({
                "message": f"Plugin registry synced. {created_count} new plugin(s) added. {total} total in DB."
            })

        if action == "verify_audit":
            from .tasks import verify_audit_log_integrity
            task = verify_audit_log_integrity.delay(force=True)
            return self.success_response({
                "message": "Audit log integrity verification task queued.",
                "task_id": task.id
            })

        if action == "backfill_audit":
            from .tasks import backfill_audit_logs
            task = backfill_audit_logs.delay()
            return self.success_response({
                "message": "Audit log backfill task queued in background.",
                "task_id": task.id
            })

        if action == "repair_audit":
            from .tasks import repair_audit_chain_task
            task = repair_audit_chain_task.delay()
            return self.success_response({
                "message": "Audit chain repair task queued in background.",
                "task_id": task.id
            })

        return self.error_response("Invalid maintenance action.")

@method_decorator(superadmin_required, name='dispatch')
class GlobalAdminCTLogsView(BaseView):
    """GET /v1/admin/ct-logs/ — View CT Logs discovery stats."""
    def get(self, request):
        total = ScanTarget.objects.filter(tags__contains="ct-log").count()
        targets = ScanTarget.objects.filter(tags__contains="ct-log").select_related('workspace').order_by("-created_at")[:50]
        
        return self.success_response({
            "status": "active",
            "total_discovered": total,
            "recent_targets": [
                {
                    "id": str(t.id),
                    "host": t.host,
                    "workspace": t.workspace.name,
                    "created_at": t.created_at.isoformat() if t.created_at else None
                } for t in targets
            ]
        })

@method_decorator(superadmin_required, name='dispatch')
class GlobalAdminScanPluginViewSet(BaseView):
    """GET/PATCH /v1/admin/strategies/ — Manage scan strategies/plugins."""
    def get(self, request, pk=None):
        if pk:
            plugin = get_object_or_404(ScanPlugin, pk=pk)
            return self.success_response(GlobalAdminScanPluginSerializer(plugin).data)
        plugins = ScanPlugin.objects.all().order_by("name")
        return self.success_response(GlobalAdminScanPluginSerializer(plugins, many=True).data)

    def patch(self, request, pk):
        plugin = get_object_or_404(ScanPlugin, pk=pk)
        ser = GlobalAdminScanPluginSerializer(plugin, data=self.json_body, partial=True)
        if ser.is_valid():
            ser.save()
            return self.success_response(ser.data)
        return self.error_response(ser.errors)
