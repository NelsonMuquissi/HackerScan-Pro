from rest_framework import status, views
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from scans.models import Finding
from scans.views import WorkspaceScopedViewMixin
from core.permissions import IsWorkspaceMember
from marketplace.services import has_module_access
from billing.services import BillingService
from .services import ai_service

class AIExplanationView(WorkspaceScopedViewMixin, views.APIView):
    """
    Returns an AI-generated explanation for a finding.
    """
    permission_classes = [IsWorkspaceMember]

    def post(self, request, finding_id):
        wid = self.get_workspace_id(request)
        finding = get_object_or_404(Finding, id=finding_id, scan__target__workspace_id=wid)
        
        # Check if explanation already exists (caching in DB)
        if finding.ai_explanation:
            return Response({"explanation": finding.ai_explanation})
            
        allowed, reason = BillingService.check_quota(finding.scan.target.workspace, "api_call")
        if not allowed:
            return Response({"detail": reason}, status=status.HTTP_402_PAYMENT_REQUIRED)
            
        # Generate via service
        explanation = ai_service.explain_finding(
            finding.title, 
            finding.description, 
            finding.severity
        )
        
        # Save to DB
        finding.ai_explanation = explanation
        finding.save()
        
        BillingService.increment_usage(finding.scan.target.workspace, "api_calls_count")
        
        return Response({"explanation": explanation})

class AIRemediationView(WorkspaceScopedViewMixin, views.APIView):
    """
    Returns an AI-generated remediation guide for a finding.
    """
    permission_classes = [IsWorkspaceMember]

    def post(self, request, finding_id):
        wid = self.get_workspace_id(request)
        finding = get_object_or_404(Finding, id=finding_id, scan__target__workspace_id=wid)
        
        if finding.ai_remediation:
            return Response({"remediation": finding.ai_remediation})
            
        allowed, reason = BillingService.check_quota(finding.scan.target.workspace, "api_call")
        if not allowed:
            return Response({"detail": reason}, status=status.HTTP_402_PAYMENT_REQUIRED)
            
        remediation = ai_service.get_remediation_guide(
            finding.title, 
            finding.description
        )
        
        finding.ai_remediation = remediation
        finding.save()
        
        BillingService.increment_usage(finding.scan.target.workspace, "api_calls_count")
        
        return Response({"remediation": remediation})

class AIScanPredictionView(WorkspaceScopedViewMixin, views.APIView):
    """
    Analyzes all findings for a scan and predicts potential attack chains.
    """
    permission_classes = [IsWorkspaceMember]

    def post(self, request, scan_id):
        from scans.models import Scan, Finding # noqa: PLC0415
        wid = self.get_workspace_id(request)
        scan = get_object_or_404(Scan, id=scan_id, target__workspace_id=wid)
        
        # Enforce Marketplace Gating
        if not has_module_access(scan.target.workspace, "ai-intelligence"):
            return Response(
                {"detail": "Marketplace Upgrade Required. Purchase the AI Intelligence module to unlock attack chain predictions."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        allowed, reason = BillingService.check_quota(scan.target.workspace, "api_call")
        if not allowed:
            return Response({"detail": reason}, status=status.HTTP_402_PAYMENT_REQUIRED)
        
        # Check cache in scan model (we'll need to add this field or use cache)
        # For now, we'll use a local cache key to avoid hitting AI too often
        from django.core.cache import cache # noqa: PLC0415
        cache_key = f"ai_prediction_{scan_id}"
        cached_prediction = cache.get(cache_key)
        
        if cached_prediction:
            return Response({"prediction": cached_prediction})

        # Get findings for this scan
        findings_qs = Finding.objects.filter(scan=scan, status='active').order_by('-severity')[:15]
        findings_data = [
            {
                "title": f.title,
                "severity": f.severity,
                "description": f.description
            }
            for f in findings_qs
        ]

        if not findings_data:
            return Response({
                "prediction": "Nenhum finding ativo encontrado para análise de cadeia de ataque."
            })

        prediction = ai_service.predict_attack_chains(findings_data)
        
        # Cache the result for 1 hour
        cache.set(cache_key, prediction, 3600)
        BillingService.increment_usage(scan.target.workspace, "api_calls_count")
        
        return Response({"prediction": prediction})
