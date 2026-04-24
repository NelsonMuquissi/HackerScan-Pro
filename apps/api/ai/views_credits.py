from rest_framework import status, views, generics
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
import stripe

from scans.views import WorkspaceScopedViewMixin
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsWorkspaceMember, IsWorkspaceAdmin
from .models import (
    AIWallet, 
    AITransaction, 
    CreditPackage, 
    Achievement, 
    WorkspaceAchievement
)
from .serializers import (
    AIWalletSerializer, 
    AITransactionSerializer, 
    CreditPackageSerializer, 
    AchievementSerializer,
    WorkspaceAchievementSerializer
)

stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

class AIWalletView(WorkspaceScopedViewMixin, views.APIView):
    """
    GET: Returns the workspace AI wallet balance and settings.
    PATCH: Updates wallet settings (auto-reload, express mode).
    """
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        wid = self.get_workspace_id(request)
        wallet, _ = AIWallet.objects.get_or_create(workspace_id=wid)
        serializer = AIWalletSerializer(wallet)
        return Response(serializer.data)

    def patch(self, request):
        self.permission_classes = [IsWorkspaceAdmin]
        wid = self.get_workspace_id(request)
        wallet = get_object_or_404(AIWallet, workspace_id=wid)
        
        allowed_fields = ['auto_reload_enabled', 'auto_reload_threshold', 'auto_reload_package', 'express_mode_enabled']
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        
        serializer = AIWalletSerializer(wallet, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AITransactionListView(WorkspaceScopedViewMixin, generics.ListAPIView):
    """
    Returns a paginated list of AI credit transactions for the workspace.
    """
    serializer_class = AITransactionSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        wid = self.get_workspace_id(self.request)
        return AITransaction.objects.filter(workspace_id=wid).order_by('-created_at')

class CreditPackageListView(generics.ListAPIView):
    """
    Lists all active credit packages available for purchase.
    """
    serializer_class = CreditPackageSerializer
    queryset = CreditPackage.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated] # Accessible by any logged user

class AchievementListView(WorkspaceScopedViewMixin, views.APIView):
    """
    Returns all achievements and marks those already unlocked by the workspace.
    """
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        wid = self.get_workspace_id(request)
        achievements = Achievement.objects.filter(is_active=True)
        unlocked_ids = WorkspaceAchievement.objects.filter(
            workspace_id=wid
        ).values_list('achievement_id', flat=True)
        
        data = []
        for a in achievements:
            data.append({
                "id": a.id,
                "slug": a.slug,
                "name": a.name,
                "description": a.description,
                "icon": a.icon,
                "credits": a.credits,
                "is_unlocked": a.id in unlocked_ids
            })
        
        return Response(data)

class CreditCheckoutView(WorkspaceScopedViewMixin, views.APIView):
    """
    Creates a Stripe Checkout Session for purchasing a credit package.
    """
    permission_classes = [IsWorkspaceAdmin]

    def post(self, request):
        wid = self.get_workspace_id(request)
        package_slug = request.data.get('package_slug')
        package = get_object_or_404(CreditPackage, slug=package_slug, is_active=True)
        
        # In a real scenario, we'd use the frontend URL from settings
        success_url = request.data.get('success_url', f"{settings.FRONTEND_URL}/settings/billing?status=success")
        cancel_url = request.data.get('cancel_url', f"{settings.FRONTEND_URL}/settings/billing?status=cancel")

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f"HackerScan Pro - {package.name} ({package.credits} AI Credits)",
                            'description': package.tagline,
                        },
                        'unit_amount': int(package.price_usd * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'workspace_id': str(wid),
                    'package_slug': package.slug,
                    'type': 'ai_credits'
                }
            )
            return Response({'url': checkout_session.url})
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
