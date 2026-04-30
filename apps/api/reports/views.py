from django.shortcuts import get_object_or_404
from rest_framework import status, views, viewsets, mixins
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Report
from .tasks import generate_scan_report
from scans.models import Scan
from scans.views import WorkspaceScopedViewMixin
from core.permissions import IsWorkspaceMember
from .serializers import ReportSerializer
from users.models import AuditLog

class ReportCreateView(WorkspaceScopedViewMixin, views.APIView):
    """
    POST /v1/scans/<id>/report/
    Request a new report generation.
    """
    permission_classes = [IsWorkspaceMember]

    def post(self, request, scan_id):
        from users.models import UserRole  # noqa: PLC0415
        is_global_admin = request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]
        
        if is_global_admin:
            scan = get_object_or_404(Scan, id=scan_id)
        else:
            scan = get_object_or_404(Scan, id=scan_id, target__workspace_id=wid)
        
        report_type = request.data.get('type', Report.Type.TECHNICAL)
        report_format = request.data.get('format', Report.Format.PDF)

        report = Report.objects.create(
            scan=scan,
            type=report_type,
            format=report_format
        )

        # Trigger Celery task
        generate_scan_report.delay(report.id)

        AuditLog.log(
            user=request.user,
            action="report.create",
            workspace=scan.target.workspace,
            resource_type="Report",
            resource_id=report.id,
            metadata={
                "scan_id": str(scan.id),
                "type": report_type,
                "format": report_format
            }
        )

        return Response(
            {
                "message": "Report generation initiated.",
                "report_id": str(report.id),
                "id": str(report.id),
                "status": report.status
            },
            status=status.HTTP_202_ACCEPTED
        )


class ReportViewSet(WorkspaceScopedViewMixin,
                    mixins.ListModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.DestroyModelMixin,
                    viewsets.GenericViewSet):
    """
    API for managing generated reports.
    GET /v1/reports/
    GET /v1/reports/<id>/
    """
    serializer_class = ReportSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        from users.models import UserRole  # noqa: PLC0415
        if self.request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            return Report.objects.all().select_related("scan", "scan__target")
            
        wid = self.get_workspace_id(self.request)
        return Report.objects.filter(scan__target__workspace_id=wid).select_related("scan", "scan__target")

# Detailed view is now handled by ReportViewSet.
# Removed ReportDetailView to avoid redundancy.
