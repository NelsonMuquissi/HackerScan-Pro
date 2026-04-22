from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from core.permissions import IsWorkspaceAdmin, IsWorkspaceMember
from scans.views import WorkspaceScopedViewMixin
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
        wid = self.get_workspace_id(self.request)
        return BountyProgram.objects.filter(workspace_id=wid)

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied
        from billing.services import BillingService
        from users.models import Workspace

        wid = self.get_workspace_id(self.request)
        workspace = Workspace.objects.get(id=wid)
        
        allowed, reason = BillingService.check_quota(workspace, "create_bounty")
        if not allowed:
            raise PermissionDenied(reason)
            
        serializer.save(workspace=workspace)

class WorkspaceSubmissionViewSet(WorkspaceScopedViewMixin, viewsets.ReadOnlyModelViewSet):
    """
    Admin view for triaging submissions in a workspace.
    """
    serializer_class = BountySubmissionSerializer
    permission_classes = [IsWorkspaceAdmin]

    def get_queryset(self):
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
        
        return Response(BountySubmissionSerializer(submission).data)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark as resolved and finalize payout."""
        submission = self.get_object()
        submission.status = BountySubmission.Status.RESOLVED
        submission.save()
        
        # In production: trigger payment via Stripe or similar
        return Response({"status": "resolved", "message": "Submission marked as resolved."})

class ResearcherSubmissionViewSet(viewsets.ModelViewSet):
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

    def get_object_handle(self, pk):
        return get_object_or_404(BountySubmission, pk=pk, researcher=self.request.user)
