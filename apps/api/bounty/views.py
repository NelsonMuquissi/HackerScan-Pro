from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from core.permissions import IsWorkspaceAdmin, IsWorkspaceMember
from scans.views import WorkspaceScopedViewMixin
from core.mixins.audit import AuditLoggerMixin
from users.models import AuditLog
from users.serializers import AuditLogSerializer
from .models import BountyProgram, BountySubmission
from .serializers import (
    BountyProgramSerializer, 
    BountySubmissionSerializer,
    BountySubmissionCreateSerializer
)
from .tasks import verify_bounty_submission_task

class PublicProgramViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and view active bounty programs (Researcher view).
    """
    queryset = BountyProgram.objects.filter(status=BountyProgram.Status.ACTIVE)
    serializer_class = BountyProgramSerializer
    permission_classes = [permissions.IsAuthenticated]

class WorkspaceBountyViewSet(WorkspaceScopedViewMixin, viewsets.ModelViewSet):
    """
    Admin view for managing workspace bounty programs.
    """
    serializer_class = BountyProgramSerializer
    permission_classes = [IsWorkspaceAdmin]

    def get_queryset(self):
        from users.models import UserRole  # noqa: PLC0415
        if self.request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            return BountyProgram.objects.all()
            
        wid = self.get_workspace_id(self.request)
        return BountyProgram.objects.filter(workspace_id=wid)

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied
        from billing.services import BillingService
        from users.models import Workspace

        wid = self.get_workspace_id(self.request)
        workspace = Workspace.objects.get(id=wid)
        
        allowed, reason = BillingService.check_quota(workspace, "create_bounty", user=self.request.user)
        if not allowed:
            raise PermissionDenied(reason)
            
        serializer.save(workspace=workspace)

class WorkspaceSubmissionViewSet(WorkspaceScopedViewMixin, AuditLoggerMixin, viewsets.ReadOnlyModelViewSet):
    """
    Admin view for triaging submissions in a workspace.
    """
    serializer_class = BountySubmissionSerializer
    permission_classes = [IsWorkspaceAdmin]

    def get_queryset(self):
        from users.models import UserRole  # noqa: PLC0415
        if self.request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            return BountySubmission.objects.all()
            
        wid = self.get_workspace_id(self.request)
        return BountySubmission.objects.filter(program__workspace_id=wid)

    @action(detail=True, methods=['post'])
    def triage(self, request, pk=None):
        """Set severity, payout amount, and internal notes."""
        submission = self.get_object()
        
        severity = request.data.get('severity')
        payout = request.data.get('payout_amount')
        notes = request.data.get('internal_notes')
        
        if severity:
            submission.severity = severity
        if payout is not None:
            submission.payout_amount = payout
        if notes:
            submission.internal_notes = notes
            
        submission.status = BountySubmission.Status.TRIAGED
        submission.save()
        
        # Log the triage using mixin
        self.log_audit_action(
            action="bounty.submission.triage",
            resource_type="BountySubmission",
            resource_id=submission.id,
            metadata={
                "severity": submission.severity,
                "payout": str(submission.payout_amount)
            }
        )
        
        return Response(BountySubmissionSerializer(submission).data)

    @action(detail=True, methods=['get'])
    def verify_integrity(self, request, pk=None):
        """Verify the digital fingerprint of the submission."""
        submission = self.get_object()
        is_valid = submission.verify_integrity()
        
        # Log the integrity verification
        self.log_audit_action(
            action="bounty.submission.verify_integrity",
            resource_type="BountySubmission",
            resource_id=submission.id,
            metadata={"is_valid": is_valid, "hash": submission.verification_hash}
        )
        
        return Response({
            "is_valid": is_valid,
            "hash": submission.verification_hash,
            "timestamp": submission.created_at
        })

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark as resolved and finalize payout."""
        submission = self.get_object()
        submission.status = BountySubmission.Status.RESOLVED
        submission.save()
        
        # Log the resolution using mixin
        self.log_audit_action(
            action="bounty.submission.resolve",
            resource_type="BountySubmission",
            resource_id=submission.id,
            metadata={"payout": str(submission.payout_amount)}
        )
        
        # In production: trigger payment via Stripe or similar
        return Response({"status": "resolved", "message": "Submission marked as resolved."})

    @action(detail=True, methods=['post'])
    def generate_certificate(self, request, pk=None):
        """Generate and save the compliance certificate PDF."""
        from django.core.files.base import ContentFile
        from reports.generators.pdf import PDFGenerator
        
        submission = self.get_object()
        pdf_bytes = PDFGenerator.generate_bounty_certificate(submission)
        
        cert_name = f"compliance_cert_{str(submission.id)[:8]}.pdf"
        submission.compliance_certificate.save(cert_name, ContentFile(pdf_bytes), save=True)
        
        # Log the certificate generation
        self.log_audit_action(
            action="bounty.submission.generate_certificate",
            resource_type="BountySubmission",
            resource_id=submission.id,
            metadata={"filename": cert_name}
        )
        
        return Response({
            "status": "success",
            "certificate_url": submission.compliance_certificate.url
        })

class ResearcherSubmissionViewSet(AuditLoggerMixin, viewsets.ModelViewSet):
    """
    Manage researcher's own submissions.
    """
    serializer_class = BountySubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BountySubmission.objects.filter(researcher=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = BountySubmissionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Save submission
        submission = serializer.save(researcher=self.request.user)
        
        # Trigger background verification task
        verify_bounty_submission_task.delay(str(submission.id))
        
        # Log the submission using mixin
        self.log_audit_action(
            action="bounty.submission.create",
            resource_type="BountySubmission",
            resource_id=submission.id,
            metadata={"title": submission.title}
        )
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            BountySubmissionSerializer(submission).data, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )

    @action(detail=True, methods=['post'])
    def verify_proof(self, request, pk=None):
        """Manually trigger verification check."""
        submission = self.get_object()
        
        # Trigger background task
        verify_bounty_submission_task.delay(str(submission.id))
        
        return Response({
            "status": "pending", 
            "message": "Verification task queued. Please check back in a few seconds."
        })

    @action(detail=True, methods=['get'])
    def verify_integrity(self, request, pk=None):
        """Verify the digital fingerprint of the submission."""
        submission = self.get_object()
        is_valid = submission.verify_integrity()
        
        # Log the integrity verification
        self.log_audit_action(
            action="bounty.submission.verify_integrity",
            resource_type="BountySubmission",
            resource_id=submission.id,
            metadata={"is_valid": is_valid, "hash": submission.verification_hash}
        )
        
        return Response({
            "is_valid": is_valid,
            "hash": submission.verification_hash,
            "timestamp": submission.created_at
        })

    @action(detail=True, methods=['post'])
    def generate_certificate(self, request, pk=None):
        """Generate and save the compliance certificate PDF."""
        from django.core.files.base import ContentFile
        from reports.generators.pdf import PDFGenerator
        
        submission = self.get_object()
        pdf_bytes = PDFGenerator.generate_bounty_certificate(submission)
        
        cert_name = f"compliance_cert_{str(submission.id)[:8]}.pdf"
        submission.compliance_certificate.save(cert_name, ContentFile(pdf_bytes), save=True)
        
        # Log the certificate generation
        self.log_audit_action(
            action="bounty.submission.generate_certificate",
            resource_type="BountySubmission",
            resource_id=submission.id,
            metadata={"filename": cert_name}
        )
        
        return Response({
            "status": "success",
            "certificate_url": submission.compliance_certificate.url
        })

    @action(detail=True, methods=['post'])
    def upload_attachment(self, request, pk=None):
        """Upload a technical attachment (PCAP, LOG, etc.) for this submission."""
        import hashlib
        from .models import BountyAttachment
        
        submission = self.get_object()
        file_obj = request.FILES.get('file')
        
        if not file_obj:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)
            
        # Calculate hash for integrity
        hasher = hashlib.sha256()
        for chunk in file_obj.chunks():
            hasher.update(chunk)
        file_hash = hasher.hexdigest()
        
        attachment = BountyAttachment.objects.create(
            submission=submission,
            file=file_obj,
            filename=file_obj.name,
            file_type=file_obj.content_type,
            file_size=file_obj.size,
            file_hash=file_hash
        )
        
        # Log the attachment upload
        self.log_audit_action(
            action="bounty.submission.upload_attachment",
            resource_type="BountySubmission",
            resource_id=submission.id,
            metadata={"filename": attachment.filename, "hash": attachment.file_hash}
        )
        
        return Response({
            "id": attachment.id,
            "filename": attachment.filename,
            "hash": attachment.file_hash,
            "url": attachment.file.url
        })

    def get_object_handle(self, pk):
        return get_object_or_404(BountySubmission, pk=pk, researcher=self.request.user)

class TransparencyLogView(generics.ListAPIView):
    """
    Exposes a read-only log of all bounty-related actions for transparency.
    """
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Filter for bounty actions to ensure researchers and users can see the audit trail
        queryset = AuditLog.objects.filter(action__startswith="bounty.").order_by("-created_at")
        
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
            
        resource_id = self.request.query_params.get('resource_id')
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)
            
        return queryset

class TransparencyLogExportView(generics.GenericAPIView):
    """
    Exports the transparency log as CSV for regulatory reporting and offline auditing.
    Restricted to SUPERADMIN users only.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        import csv
        from django.http import HttpResponse
        from users.models import UserRole
        
        # Security Gate: Only superadmins can export the full immutable log
        if request.user.role != UserRole.SUPERADMIN:
            return Response(
                {"error": "Unauthorized. Higher clearance required for audit export."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = AuditLog.objects.filter(action__startswith="bounty.").order_by("-created_at")
        
        # Apply filters from query params
        action_filter = request.query_params.get('action')
        if action_filter:
            queryset = queryset.filter(action=action_filter)
            
        resource_id = request.query_params.get('resource_id')
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="bounty_transparency_log.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Timestamp', 'Action', 'User', 'Workspace', 
            'Resource Type', 'Resource ID', 'IP Address', 
            'Prev Hash', 'Current Hash', 'Metadata'
        ])

        for log in queryset:
            writer.writerow([
                log.id,
                log.created_at.isoformat(),
                log.action,
                log.user.email if log.user else "System",
                log.workspace.name if log.workspace else "Global",
                log.resource_type,
                log.resource_id,
                log.ip_address,
                log.previous_hash,
                log.current_hash,
                str(log.metadata)
            ])

        return response
