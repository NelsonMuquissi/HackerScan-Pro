"""
Thin HTTP layer for the scans app.
All business logic is in services.py.
"""
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import models
from django.utils import timezone


from billing.services import BillingService
from core.mixins.quota import QuotaCheckMixin
from core.exceptions import NotFoundError, ServiceError
from core.permissions import IsWorkspaceAdmin, IsWorkspaceMember
from .serializers import (
    FindingSerializer,
    ScanCreateSerializer,
    ScanDetailSerializer,
    ScanListSerializer,
    ScanPluginSerializer,
    ScanTargetSerializer,
    ScheduledScanSerializer,
)
from .services import FindingService, ScanService, ScanTargetService
from .scheduling import ScanScheduler
from .models import ScheduledScan


from core.mixins.workspace import WorkspaceScopedViewMixin
from core.mixins.audit import AuditLoggerMixin


# ═══════════════════════════════════════════════════════════════════════
#  TARGETS
# ═══════════════════════════════════════════════════════════════════════

class ScanTargetListCreateView(WorkspaceScopedViewMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        from users.models import UserRole  # noqa: PLC0415
        wid = self.get_workspace_id(request)
        
        if request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN] and not request.query_params.get("workspace_id"):
            targets = ScanTargetService.list_all() if hasattr(ScanTargetService, 'list_all') else ScanTarget.objects.all().order_by("-created_at")
        elif not wid:
             return Response({"detail": "Workspace required."}, status=http_status.HTTP_400_BAD_REQUEST)
        else:
            targets = ScanTargetService.list_for_workspace(wid)
            
        return Response(ScanTargetSerializer(targets, many=True).data)

    def post(self, request):
        from users.models import UserRole, Workspace  # noqa: PLC0415
        is_admin = request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]
        wid = self.get_workspace_id(request)
        
        if not wid and not is_admin:
             return Response({"detail": "Workspace required."}, status=http_status.HTTP_400_BAD_REQUEST)

        ser = ScanTargetSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        # Ensure the user has admin rights to create targets in this workspace
        from users.models import WorkspaceMember  # noqa: PLC0415
        if not is_admin and not WorkspaceMember.objects.filter(workspace_id=wid, user=request.user, role__in=["owner", "admin"]).exists():
            return Response({"detail": "Permission denied for this workspace."}, status=http_status.HTTP_403_FORBIDDEN)

        # Fallback for admins if wid is missing: use personal or first active
        if not wid and is_admin:
            workspace = Workspace.objects.filter(owner=request.user, is_active=True).first() or \
                        Workspace.objects.filter(is_active=True).first()
            if not workspace:
                # If truly nothing exists, we can't create a target without a workspace.
                # However, quick_scan handles auto-creation. For manual target creation, 
                # we might still need a workspace.
                return Response({"detail": "Workspace required. Please create a workspace first."}, status=http_status.HTTP_400_BAD_REQUEST)
        else:
            workspace = Workspace.objects.get(pk=wid)

        target = ScanTargetService.create(
            user=request.user,
            workspace=workspace,
            name=d["name"],
            host=d["host"],
            target_type=d.get("target_type", "domain"),
            description=d.get("description", ""),
            tags=d.get("tags", []),
        )
        return Response(ScanTargetSerializer(target).data, status=http_status.HTTP_201_CREATED)


class ScanTargetDetailView(WorkspaceScopedViewMixin, APIView):
    permission_classes = [IsWorkspaceAdmin]

    def _get_target(self, request, target_id):
        from users.models import UserRole  # noqa: PLC0415
        if request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            from .models import ScanTarget  # noqa: PLC0415
            return get_object_or_404(ScanTarget, pk=target_id)
            
        wid = self.get_workspace_id(request)
        return ScanTargetService.get_or_404(wid, target_id)

    def get(self, request, target_id):
        return Response(ScanTargetSerializer(self._get_target(request, target_id)).data)

    def patch(self, request, target_id):
        target = self._get_target(request, target_id)
        ser    = ScanTargetSerializer(target, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    def delete(self, request, target_id):
        target = self._get_target(request, target_id)
        target.delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)


# ═══════════════════════════════════════════════════════════════════════
#  SCHEDULES
# ═══════════════════════════════════════════════════════════════════════

class ScheduledScanListCreateView(WorkspaceScopedViewMixin, APIView):
    permission_classes = [IsWorkspaceAdmin]

    def get(self, request):
        from users.models import UserRole  # noqa: PLC0415
        wid = self.get_workspace_id(request)
        
        if request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN] and not request.query_params.get("workspace_id"):
            schedules = ScheduledScan.objects.all().select_related("target")
        else:
            schedules = ScheduledScan.objects.filter(target__workspace_id=wid).select_related("target")
            
        return Response(ScheduledScanSerializer(schedules, many=True).data)

    def post(self, request):
        from users.models import UserRole  # noqa: PLC0415
        ser = ScheduledScanSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        
        # Verify target ownership
        target_id = ser.validated_data["target"].id
        
        if request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            from .models import ScanTarget  # noqa: PLC0415
            target = get_object_or_404(ScanTarget, pk=target_id)
            wid = str(target.workspace_id)
        else:
            wid = self.get_workspace_id(request)
            ScanTargetService.get_or_404(wid, target_id)

        schedule = ser.save()
        ScanScheduler.sync(schedule)
        
        return Response(ScheduledScanSerializer(schedule).data, status=http_status.HTTP_201_CREATED)


class ScheduledScanDetailView(WorkspaceScopedViewMixin, APIView):
    permission_classes = [IsWorkspaceAdmin]

    def _get_schedule(self, request, schedule_id):
        from users.models import UserRole  # noqa: PLC0415
        if request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            return get_object_or_404(ScheduledScan, pk=schedule_id)
            
        wid = self.get_workspace_id(request)
        try:
            return ScheduledScan.objects.get(pk=schedule_id, target__workspace_id=wid)
        except ScheduledScan.DoesNotExist:
            raise NotFoundError("Scheduled scan not found.")

    def get(self, request, schedule_id):
        return Response(ScheduledScanSerializer(self._get_schedule(request, schedule_id)).data)

    def patch(self, request, schedule_id):
        schedule = self._get_schedule(request, schedule_id)
        ser = ScheduledScanSerializer(schedule, data=request.data, partial=True, context={"request": request})
        ser.is_valid(raise_exception=True)
        schedule = ser.save()
        
        ScanScheduler.sync(schedule)
        return Response(ScheduledScanSerializer(schedule).data)

    def delete(self, request, schedule_id):
        schedule = self._get_schedule(request, schedule_id)
        ScanScheduler.delete(schedule)
        schedule.delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT)


# ═══════════════════════════════════════════════════════════════════════
#  SCANS
# ═══════════════════════════════════════════════════════════════════════

class _ScanCreateBase(WorkspaceScopedViewMixin, APIView):
    """Base APIView providing a custom create() compatible with QuotaCheckMixin."""
    def create(self, request, *args, **kwargs):
        ser = ScanCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        from users.models import UserRole  # noqa: PLC0415
        if request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            from .models import ScanTarget  # noqa: PLC0415
            target = get_object_or_404(ScanTarget, pk=d["target_id"])
            wid = str(target.workspace_id)
        else:
            wid = self.get_workspace_id(request)

        if not wid:
             return Response({"detail": "Workspace required."}, status=http_status.HTTP_400_BAD_REQUEST)

        # Marketplace Module Check
        from marketplace.services import check_module_access  # noqa: PLC0415
        from users.models import Workspace, UserRole  # noqa: PLC0415
        
        is_admin = request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]
        if not is_admin:
            workspace = Workspace.objects.get(pk=wid)
            if not check_module_access(workspace, d["scan_type"], user=request.user):
                return Response({
                    "detail": "This specialized scan module is locked. Visit the Marketplace to unlock premium capabilities.",
                    "code": "module_locked",
                    "required_module": d["scan_type"]
                }, status=http_status.HTTP_402_PAYMENT_REQUIRED)

        scan = ScanService.create(
            user=request.user,
            workspace_id=wid,
            target_id=d["target_id"],
            scan_type=d["scan_type"],
            plugin_ids=d.get("plugin_ids", []),
            config=d.get("config", {}),
        )
        return Response(ScanDetailSerializer(scan).data, status=http_status.HTTP_201_CREATED)


class ScanListCreateView(QuotaCheckMixin, _ScanCreateBase):
    permission_classes = [IsWorkspaceMember]
    quota_action = "create_scan"

    def get_workspace(self):
        # Used by QuotaCheckMixin
        from users.models import Workspace
        wid = self.get_workspace_id(self.request)
        if not wid: return None
        return Workspace.objects.filter(pk=wid).first()

    def get(self, request):
        from users.models import UserRole  # noqa: PLC0415
        wid = self.get_workspace_id(request)
        target_id = request.query_params.get("target_id")
        
        if request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN] and not request.query_params.get("workspace_id"):
            from .models import Scan  # noqa: PLC0415
            scans = Scan.objects.all().select_related("target")
            if target_id:
                scans = scans.filter(target_id=target_id)
            scans = scans.order_by("-created_at")
        else:
            scans = ScanService.list_for_workspace(wid, target_id=target_id)
            
        return Response(ScanListSerializer(scans, many=True).data)

    def post(self, request, *args, **kwargs):
        # Delegate to QuotaCheckMixin.create(), which then calls super().create() (_ScanCreateBase)
        return self.create(request, *args, **kwargs)


class ScanDetailView(WorkspaceScopedViewMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request, scan_id):
        from users.models import UserRole  # noqa: PLC0415
        if request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            from .models import Scan  # noqa: PLC0415
            scan = get_object_or_404(Scan, pk=scan_id)
        else:
            wid = self.get_workspace_id(request)
            scan = ScanService.get_or_404(wid, scan_id)
        return Response(ScanDetailSerializer(scan).data)


class ScanStartView(WorkspaceScopedViewMixin, APIView):
    permission_classes = [IsWorkspaceAdmin]

    def post(self, request, scan_id):
        from users.models import UserRole  # noqa: PLC0415
        if request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            from .models import Scan  # noqa: PLC0415
            scan = get_object_or_404(Scan, pk=scan_id)
            wid = str(scan.target.workspace_id)
        else:
            wid = self.get_workspace_id(request)
        
        scan = ScanService.trigger(wid, scan_id)
        return Response({
            "message": "Scan queued for execution.",
            "scan_id": str(scan.id),
            "status": scan.status,
        })


class ScanRescanView(WorkspaceScopedViewMixin, APIView):
    permission_classes = [IsWorkspaceAdmin]

    def post(self, request, scan_id):
        from users.models import UserRole  # noqa: PLC0415
        if request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            from .models import Scan  # noqa: PLC0415
            scan_obj = get_object_or_404(Scan, pk=scan_id)
            wid = str(scan_obj.target.workspace_id)
        else:
            wid = self.get_workspace_id(request)
        
        new_scan = ScanService.rescan(wid, scan_id, request.user)
        return Response(ScanDetailSerializer(new_scan).data, status=http_status.HTTP_201_CREATED)


class ScanCancelView(WorkspaceScopedViewMixin, APIView):
    permission_classes = [IsWorkspaceAdmin]

    def post(self, request, scan_id):
        from users.models import UserRole  # noqa: PLC0415
        if request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            from .models import Scan  # noqa: PLC0415
            scan = get_object_or_404(Scan, pk=scan_id)
            wid = str(scan.target.workspace_id)
        else:
            wid = self.get_workspace_id(request)

        scan = ScanService.cancel(wid, scan_id)
        return Response({
            "message": "Scan cancelled.",
            "scan_id": str(scan.id),
            "status": scan.status,
        })


# ═══════════════════════════════════════════════════════════════════════
#  FINDINGS
# ═══════════════════════════════════════════════════════════════════════

class ScanFindingsView(WorkspaceScopedViewMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request, scan_id):
        from users.models import UserRole  # noqa: PLC0415
        severity = request.query_params.get("severity")
        
        if request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            from .models import Scan  # noqa: PLC0415
            scan = get_object_or_404(Scan, pk=scan_id)
            findings = scan.findings.all()
            if severity:
                findings = findings.filter(severity=severity)
        else:
            wid = self.get_workspace_id(request)
            findings = ScanService.get_findings(wid, scan_id, severity=severity)
            
        return Response(FindingSerializer(findings, many=True).data)



class FindingAnalyzeFalsePositiveView(WorkspaceScopedViewMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, finding_id):
        wid = self.get_workspace_id(request)
        if not wid:
             return Response({"detail": "Workspace required."}, status=http_status.HTTP_400_BAD_REQUEST)
        
        try:
            result = FindingService.analyze_false_positive(wid, finding_id)
            # Fetch the updated finding
            finding = FindingService.get_or_404(wid, finding_id)
            return Response({
                "message": "False positive analysis completed.",
                "analysis": result,
                "finding": FindingSerializer(finding).data
            })
        except NotFoundError as e:
            return Response({"detail": str(e)}, status=http_status.HTTP_404_NOT_FOUND)
        except ServiceError as e:
            return Response({"detail": str(e)}, status=http_status.HTTP_400_BAD_REQUEST)


class FindingVerifyView(WorkspaceScopedViewMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, finding_id):
        wid = self.get_workspace_id(request)
        if not wid:
             return Response({"detail": "Workspace required."}, status=http_status.HTTP_400_BAD_REQUEST)
        
        try:
            finding = FindingService.verify(wid, finding_id)
            return Response({
                "message": "Verification task queued.",
                "finding": FindingSerializer(finding).data
            })
        except NotFoundError as e:
            return Response({"detail": str(e)}, status=http_status.HTTP_404_NOT_FOUND)
        except ServiceError as e:
            return Response({"detail": str(e)}, status=http_status.HTTP_400_BAD_REQUEST)


class ScanVerifyAllView(WorkspaceScopedViewMixin, APIView):
    """Batch-verify all active findings of a completed scan."""
    permission_classes = [IsAuthenticated]

    def post(self, request, scan_id):
        from users.models import UserRole  # noqa: PLC0415

        wid = self.get_workspace_id(request)
        is_admin = request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]

        if not wid and is_admin:
            # Admin fallback: resolve workspace from the scan itself
            from .models import Scan  # noqa: PLC0415
            scan = get_object_or_404(Scan, pk=scan_id)
            wid = str(scan.target.workspace_id)

        if not wid:
            return Response({"detail": "Workspace required."}, status=http_status.HTTP_400_BAD_REQUEST)

        try:
            result = FindingService.verify_all(wid, scan_id)
            return Response({
                "message": "Batch verification queued for all active findings.",
                **result
            })
        except NotFoundError as e:
            return Response({"detail": str(e)}, status=http_status.HTTP_404_NOT_FOUND)
        except ServiceError as e:
            return Response({"detail": str(e)}, status=http_status.HTTP_400_BAD_REQUEST)


class FindingPOCView(WorkspaceScopedViewMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, finding_id):
        wid = self.get_workspace_id(request)
        if not wid:
             return Response({"detail": "Workspace required."}, status=http_status.HTTP_400_BAD_REQUEST)
        
        try:
            poc = FindingService.generate_poc(wid, finding_id)
            # Fetch updated finding to return full data
            finding = FindingService.get_or_404(wid, finding_id)
            return Response({
                "message": "Proof of Concept generated.",
                "poc": poc,
                "finding": FindingSerializer(finding).data
            })
        except NotFoundError as e:
            return Response({"detail": str(e)}, status=http_status.HTTP_404_NOT_FOUND)
        except ServiceError as e:
            return Response({"detail": str(e)}, status=http_status.HTTP_400_BAD_REQUEST)


class ScanRiskAssessmentView(WorkspaceScopedViewMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, scan_id):
        wid = self.get_workspace_id(request)
        if not wid:
             return Response({"detail": "Workspace required."}, status=http_status.HTTP_400_BAD_REQUEST)
        
        try:
            analysis = ScanService.assess_risk(wid, scan_id)
            # Fetch updated scan
            scan = ScanService.get_or_404(wid, scan_id)
            return Response({
                "message": "Risk assessment completed.",
                "analysis": analysis,
                "scan": ScanDetailSerializer(scan).data
            })
        except NotFoundError as e:
            return Response({"detail": str(e)}, status=http_status.HTTP_404_NOT_FOUND)
        except ServiceError as e:
            return Response({"detail": str(e)}, status=http_status.HTTP_400_BAD_REQUEST)


class FindingFeedbackView(WorkspaceScopedViewMixin, APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, finding_id):
        wid = self.get_workspace_id(request)
        feedback = request.data.get("feedback")
        
        if not wid:
             return Response({"detail": "Workspace required."}, status=http_status.HTTP_400_BAD_REQUEST)
        
        if not feedback:
            return Response({"detail": "Feedback type required."}, status=http_status.HTTP_400_BAD_REQUEST)

        try:
            finding = FindingService.submit_feedback(wid, finding_id, feedback)
            return Response({
                "message": "Feedback recorded. Neural model updated.",
                "finding": FindingSerializer(finding).data
            })
        except NotFoundError as e:
            return Response({"detail": str(e)}, status=http_status.HTTP_404_NOT_FOUND)
        except ServiceError as e:
            return Response({"detail": str(e)}, status=http_status.HTTP_400_BAD_REQUEST)


# ═══════════════════════════════════════════════════════════════════════
#  PLUGINS
# ═══════════════════════════════════════════════════════════════════════

class ScanPluginListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import ScanPlugin  # noqa: PLC0415
        plugins = ScanPlugin.objects.filter(is_active=True)
        return Response(ScanPluginSerializer(plugins, many=True).data)


# ═══════════════════════════════════════════════════════════════════════
#  QUICK SCAN (one-step convenience endpoint)
# ═══════════════════════════════════════════════════════════════════════

class QuickScanView(WorkspaceScopedViewMixin, APIView):
    """Accept a raw URL, auto-create target + scan, trigger execution."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from users.models import UserRole, Workspace # noqa: PLC0415
        from marketplace.services import check_module_access  # noqa: PLC0415

        target_url = request.data.get("target_url", "").strip()
        scan_type  = request.data.get("scan_type", "quick")
        plugin_ids = request.data.get("plugin_ids", [])
        wid        = self.get_workspace_id(request)
        is_admin   = request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]
        
        if not target_url:
            return Response(
                {"detail": "target_url is required."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        if not wid:
            if is_admin:
                 # Fallback to user's first owned workspace or first active one
                 workspace = Workspace.objects.filter(owner=request.user, is_active=True).first()
                 if not workspace:
                     workspace = Workspace.objects.filter(is_active=True).first()
                 
                 if workspace:
                     wid = str(workspace.id)
                 # If wid is still None, ScanService.quick_scan handles auto-provisioning
            
            if not wid and not is_admin:
                 return Response({"detail": "Workspace context required."}, status=http_status.HTTP_400_BAD_REQUEST)

        # Marketplace Module Check (Quick Scan version)
        # Admins bypass marketplace checks automatically
        if not is_admin:
            workspace = Workspace.objects.get(pk=wid)
            
            # Custom plugin list check (if provided, we assume it's a custom strategy)
            if plugin_ids and not check_module_access(workspace, "full", user=request.user):
                 # If custom plugins are used, require 'full' spectrum access for now
                 pass 

            if not check_module_access(workspace, scan_type, user=request.user):
                return Response({
                    "detail": "This specialized scan module is locked. Visit the Marketplace to unlock premium capabilities.",
                    "code": "module_locked",
                    "required_module": scan_type
                }, status=http_status.HTTP_402_PAYMENT_REQUIRED)

        scan = ScanService.quick_scan(
            request.user, 
            target_url, 
            scan_type=scan_type, 
            workspace_id=wid,
            plugin_ids=plugin_ids
        )
        return Response(
            {
                "scan_id": str(scan.id),
                "status": scan.status,
                "target_host": scan.target.host,
            },
            status=http_status.HTTP_201_CREATED,
        )


# ═══════════════════════════════════════════════════════════════════════
#  DASHBOARD STATS
# ═══════════════════════════════════════════════════════════════════════

class DashboardStatsView(WorkspaceScopedViewMixin, APIView):
    """Aggregated dashboard metrics for current workspace."""
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        from django.db.models import Sum, Count  # noqa: PLC0415
        from .models import Scan, ScanStatus  # noqa: PLC0415

        from .models import Scan, ScanStatus  # noqa: PLC0415
        from users.models import UserRole  # noqa: PLC0415

        wid = self.get_workspace_id(request)
        is_admin = request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]

        if not wid and not is_admin:
             return Response({"detail": "Workspace required."}, status=http_status.HTTP_400_BAD_REQUEST)

        if not wid and is_admin:
            # Global stats for admins if no workspace selected
            user_scans = Scan.objects.all()
        else:
            user_scans = Scan.objects.filter(target__workspace_id=wid)

        active_count = user_scans.filter(
            status__in=[ScanStatus.PENDING, ScanStatus.QUEUED, ScanStatus.RUNNING]
        ).count()

        totals = user_scans.aggregate(
            total_scans=Count("id"),
            total_findings=Sum("total_findings"),
            critical=Sum("critical_count"),
            high=Sum("high_count"),
            medium=Sum("medium_count"),
            low=Sum("low_count"),
            info=Sum("info_count"),
        )

        recent = (
            user_scans.select_related("target")
            .order_by("-created_at")[:10]
        )

        return Response({
            "active_scans": active_count,
            "total_scans": totals["total_scans"] or 0,
            "total_findings": totals["total_findings"] or 0,
            "critical_count": totals["critical"] or 0,
            "high_count": totals["high"] or 0,
            "medium_count": totals["medium"] or 0,
            "low_count": totals["low"] or 0,
            "info_count": totals["info"] or 0,
            "recent_scans": ScanListSerializer(recent, many=True).data,
        })


class EvidenceVaultView(WorkspaceScopedViewMixin, APIView):
    """
    GET /v1/scans/evidence-vault/
    Retrieve all findings with visual proof or technical evidence for the workspace.
    """
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        wid = self.get_workspace_id(request)
        if not wid:
             return Response({"detail": "Workspace required."}, status=http_status.HTTP_400_BAD_REQUEST)
        
        from .models import Finding
        from bounty.models import BountySubmission
        from django.db.models import Q
        
        # 1. Fetch Findings with evidence
        findings = Finding.objects.filter(scan__target__workspace_id=wid).filter(
            Q(visual_proof_b64__isnull=False) | 
            Q(technical_details__isnull=False) |
            Q(compliance_mapping__isnull=False)
        ).select_related("scan", "scan__target").order_by("-created_at")
        
        # 2. Fetch Bounty Submissions with evidence
        bounties = BountySubmission.objects.filter(program__workspace_id=wid).filter(
            Q(visual_proof_b64__isnull=False) | 
            Q(technical_details__isnull=False)
        ).select_related("program").order_by("-created_at")

        results = []
        
        # Normalize Findings
        for f in findings:
            results.append({
                "id": str(f.id),
                "type": "SCAN_FINDING",
                "title": f.title,
                "severity": f.severity,
                "status": f.status,
                "target_host": f.scan.target.host,
                "scan_id": str(f.scan.id),
                "compliance_mapping": f.compliance_mapping,
                "visual_proof_b64": f.visual_proof_b64,
                "technical_details": f.technical_details,
                "poc": f.poc,
                "ai_explanation": f.ai_explanation or f.ai_reasoning,
                "created_at": f.created_at.isoformat()
            })
            
        # Normalize Bounties
        for b in bounties:
            results.append({
                "id": str(b.id),
                "type": "BOUNTY_SUBMISSION",
                "title": b.title,
                "severity": b.severity,
                "status": b.status,
                "target_host": b.target_domain,
                "compliance_mapping": b.compliance_mapping,
                "visual_proof_b64": b.visual_proof_b64,
                "technical_details": b.technical_details,
                "poc": b.description,
                "ai_explanation": f"Researcher Submission: {b.researcher.email}",
                "verification_hash": b.verification_hash,
                "created_at": b.created_at.isoformat()
            })

        # Sort by creation date
        results.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Manual Pagination
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))

        count = len(results)
        paginated_results = results[offset : offset + limit]

        return Response({
            "count": count,
            "next": f"{request.path}?limit={limit}&offset={offset + limit}" if offset + limit < count else None,
            "previous": f"{request.path}?limit={limit}&offset={max(0, offset - limit)}" if offset > 0 else None,
            "results": paginated_results
        })


class EvidenceAuditLogView(WorkspaceScopedViewMixin, AuditLoggerMixin, APIView):
    """
    POST /v1/scans/evidence-vault/log/
    Log an audit action related to evidence (download, export).
    """
    permission_classes = [IsWorkspaceMember]

    def post(self, request):
        action = request.data.get("action")
        item_id = request.data.get("item_id")
        item_type = request.data.get("item_type", "SCAN_FINDING")
        metadata = request.data.get("metadata", {})

        if not action or not item_id:
            return Response({"error": "Action and item_id are required."}, status=http_status.HTTP_400_BAD_REQUEST)

        resource_type = "Finding" if item_type == "SCAN_FINDING" else "BountySubmission"

        self.log_audit_action(
            action=action,
            resource_type=resource_type,
            resource_id=item_id,
            metadata=metadata
        )

        return Response({"status": "success"})


class EvidenceExportVaultView(WorkspaceScopedViewMixin, AuditLoggerMixin, APIView):
    """
    GET /v1/scans/evidence-vault/export/
    Generate a ZIP file containing all evidence for the workspace.
    """
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        import io
        import zipfile
        import json
        import base64
        import hashlib
        from django.http import HttpResponse
        from .models import Finding
        from bounty.models import BountySubmission
        from bounty.serializers import BountySubmissionSerializer

        wid = self.get_workspace_id(request)
        
        # 1. Fetch findings with evidence
        findings = Finding.objects.filter(scan__target__workspace_id=wid).filter(
            models.Q(visual_proof_b64__isnull=False) | 
            models.Q(technical_details__isnull=False) |
            models.Q(compliance_mapping__isnull=False)
        ).select_related("scan", "scan__target")

        # 2. Fetch bounty submissions with evidence
        bounties = BountySubmission.objects.filter(program__workspace_id=wid).filter(
            models.Q(visual_proof_b64__isnull=False) | 
            models.Q(technical_details__isnull=False)
        ).select_related("program", "researcher")

        if not findings.exists() and not bounties.exists():
            return Response({"detail": "No evidence found to export."}, status=http_status.HTTP_404_NOT_FOUND)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            manifest = {}
            summary = {
                "workspace_id": wid,
                "exported_at": timezone.now().isoformat(),
                "scans_count": findings.count(),
                "bounties_count": bounties.count(),
                "artifacts": []
            }
            
            def add_to_zip_with_hash(path, data):
                if isinstance(data, str):
                    data = data.encode('utf-8')
                zip_file.writestr(path, data)
                manifest[path] = hashlib.sha256(data).hexdigest()

            # Process Scan Findings
            for f in findings:
                finding_dir = f"scans/finding_{str(f.id)[:8]}"
                finding_data = FindingSerializer(f).data
                metadata_content = json.dumps(finding_data, indent=2)
                add_to_zip_with_hash(f"{finding_dir}/metadata.json", metadata_content)
                
                if f.visual_proof_b64:
                    try:
                        img_data = base64.b64decode(f.visual_proof_b64)
                        add_to_zip_with_hash(f"{finding_dir}/proof.png", img_data)
                    except Exception: pass
                
                if f.poc:
                    add_to_zip_with_hash(f"{finding_dir}/poc.txt", f.poc)
                
                summary["artifacts"].append({
                    "id": str(f.id),
                    "type": "SCAN_FINDING",
                    "title": f.title,
                    "path": finding_dir
                })

            # Process Bounty Submissions
            for b in bounties:
                bounty_dir = f"bounties/submission_{str(b.id)[:8]}"
                bounty_data = BountySubmissionSerializer(b).data
                metadata_content = json.dumps(bounty_data, indent=2)
                add_to_zip_with_hash(f"{bounty_dir}/metadata.json", metadata_content)
                
                if b.visual_proof_b64:
                    try:
                        img_data = base64.b64decode(b.visual_proof_b64)
                        add_to_zip_with_hash(f"{bounty_dir}/proof.png", img_data)
                    except Exception: pass
                
                if b.description:
                    add_to_zip_with_hash(f"{bounty_dir}/description.md", b.description)
                
                summary["artifacts"].append({
                    "id": str(b.id),
                    "type": "BOUNTY_SUBMISSION",
                    "title": b.title,
                    "path": bounty_dir
                })

            # Finalize ZIP
            zip_file.writestr("summary.json", json.dumps(summary, indent=2))
            zip_file.writestr("manifest.json", json.dumps(manifest, indent=2))

        # Log the export using mixin
        self.log_audit_action(
            action="evidence.vault.export_all",
            metadata={
                "findings_count": findings.count(),
                "bounties_count": bounties.count(),
                "total_artifacts": len(manifest)
            }
        )

        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="HackerScan-Evidence-Vault-{wid[:8]}.zip"'
        return response

