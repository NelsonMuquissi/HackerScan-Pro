from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.services import BillingService
from core.permissions import IsWorkspaceAdmin, IsWorkspaceMember
from scans.views import WorkspaceScopedViewMixin
from users.models import Workspace
from .models import SecurityModule, WorkspaceModule
from .serializers import SecurityModuleSerializer, ModuleCheckoutSerializer

class MarketplaceViewSet(WorkspaceScopedViewMixin, viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve available security modules.
    """
    queryset = SecurityModule.objects.all()
    serializer_class = SecurityModuleSerializer
    permission_classes = [IsWorkspaceMember]
    lookup_field = "slug"

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["workspace_id"] = self.get_workspace_id(self.request)
        return context

class ModuleCheckoutView(WorkspaceScopedViewMixin, APIView):
    """
    POST /v1/marketplace/modules/{slug}/checkout/
    """
    permission_classes = [IsWorkspaceAdmin]

    def post(self, request, slug):
        module = get_object_or_404(SecurityModule, slug=slug)
        serializer = ModuleCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        wid = self.get_workspace_id(request)
        workspace = get_object_or_404(Workspace, id=wid)

        if not module.stripe_price_id:
             return Response({"detail": "This module is not available for purchase yet."}, 
                             status=status.HTTP_400_BAD_REQUEST)

        checkout_url = BillingService.create_module_checkout_session(
            workspace=workspace,
            module_slug=module.slug,
            price_id=module.stripe_price_id,
            success_url=serializer.validated_data["success_url"],
            cancel_url=serializer.validated_data["cancel_url"],
        )
        
        return Response({"checkout_url": checkout_url}, status=status.HTTP_201_CREATED)
