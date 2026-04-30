from rest_framework import status, views
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from scans.models import Finding
from scans.views import WorkspaceScopedViewMixin
from core.permissions import IsWorkspaceMember
from marketplace.services import has_module_access
from billing.services import BillingService
from .services import ai_service

from .credit_service import InsufficientCreditsError

class AIExplanationView(WorkspaceScopedViewMixin, views.APIView):
    """
    Returns an AI-generated explanation for a finding.
    """
    permission_classes = [IsWorkspaceMember]

    def post(self, request, finding_id):
        wid = self.get_workspace_id(request)
        finding = get_object_or_404(Finding, id=finding_id, scan__target__workspace_id=wid)
        workspace = finding.scan.target.workspace
        
        express = request.data.get("express", False)
        
        try:
            explanation = ai_service.explain_finding(
                finding.title, 
                finding.description, 
                finding.severity,
                workspace=workspace,
                user=request.user,
                express=express
            )
            
            # Save to DB if not already there
            if not finding.ai_explanation:
                finding.ai_explanation = explanation
                finding.save(update_fields=['ai_explanation'])
                
            return Response({"explanation": explanation})
            
        except InsufficientCreditsError as e:
            return Response({
                "detail": "Créditos de IA insuficientes.",
                "needed": e.needed,
                "available": e.available,
                "shortfall": e.shortfall
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

class AIRemediationView(WorkspaceScopedViewMixin, views.APIView):
    """
    Returns an AI-generated remediation guide for a finding.
    """
    permission_classes = [IsWorkspaceMember]

    def post(self, request, finding_id):
        wid = self.get_workspace_id(request)
        finding = get_object_or_404(Finding, id=finding_id, scan__target__workspace_id=wid)
        workspace = finding.scan.target.workspace
        
        express = request.data.get("express", False)
        
        try:
            remediation = ai_service.generate_remediation_code(
                finding.title, 
                finding.description,
                workspace=workspace,
                user=request.user,
                express=express
            )
            
            if not finding.ai_remediation:
                finding.ai_remediation = remediation
                finding.save(update_fields=['ai_remediation'])
                
            return Response({"remediation": remediation})
            
        except InsufficientCreditsError as e:
            return Response({
                "detail": "Créditos de IA insuficientes.",
                "needed": e.needed,
                "available": e.available,
                "shortfall": e.shortfall
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

class AIScanPredictionView(WorkspaceScopedViewMixin, views.APIView):
    """
    Analyzes all findings for a scan and predicts potential attack chains.
    """
    permission_classes = [IsWorkspaceMember]

    def post(self, request, scan_id):
        from scans.models import Scan, Finding # noqa: PLC0415
        wid = self.get_workspace_id(request)
        scan = get_object_or_404(Scan, id=scan_id, target__workspace_id=wid)
        workspace = scan.target.workspace
        
        # Enforce Marketplace Gating (AI Intelligence module required for predictions)
        # Enforce Marketplace Gating (AI Intelligence module required for predictions)
        # For stabilization phase, we allow all workspaces to access this
        # if not has_module_access(workspace, "ai-intelligence"):
        #     return Response(
        #         {"detail": "Upgrade de Marketplace necessário. Adquira o módulo 'AI Intelligence' para desbloquear previsões de cadeia de ataque."},
        #         status=status.HTTP_403_FORBIDDEN
        #     )
            
        # Get findings for this scan
        findings_qs = Finding.objects.filter(scan=scan, status__iexact='active').order_by('-severity')[:15]
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

        express = request.data.get("express", False)

        try:
            prediction = ai_service.predict_attack_chains(
                findings_data,
                workspace=workspace,
                user=request.user,
                express=express
            )
            return Response({"prediction": prediction})
            
        except InsufficientCreditsError as e:
            return Response({
                "detail": "Créditos de IA insuficientes.",
                "needed": e.needed,
                "available": e.available,
                "shortfall": e.shortfall
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

