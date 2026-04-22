from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from core.permissions import IsWorkspaceAdmin
from scans.views import WorkspaceScopedViewMixin
from .models import Webhook
from .serializers import WebhookSerializer

class WebhookViewSet(WorkspaceScopedViewMixin, viewsets.ModelViewSet):
    """
    Manages outbound webhooks for a workspace.
    """
    serializer_class = WebhookSerializer
    permission_classes = [IsWorkspaceAdmin]

    def get_queryset(self):
        wid = self.get_workspace_id(self.request)
        return Webhook.objects.filter(workspace_id=wid)

    def perform_create(self, serializer):
        wid = self.get_workspace_id(self.request)
        serializer.save(workspace_id=wid)

    @action(detail=True, method=['post'])
    def reset_secret(self, request, pk=None):
        webhook = self.get_object()
        webhook.reset_secret()
        return Response({"secret_token": webhook.secret_token})

    @action(detail=True, method=['post'])
    def test(self, request, pk=None):
        webhook = self.get_object()
        # To be implemented: Send a ping event
        from .services import WebhookDispatcherService
        WebhookDispatcherService.dispatch(
            webhook.workspace_id, 
            "ping", 
            {"message": "Hello from HackerScan Pro!"}
        )
        return Response({"message": "Test event dispatched."})
