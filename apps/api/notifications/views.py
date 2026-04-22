from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification, NotificationPreference
from .serializers import NotificationSerializer, NotificationPreferenceSerializer
from scans.views import WorkspaceScopedViewMixin
from core.permissions import IsWorkspaceMember, IsWorkspaceAdmin

class NotificationViewSet(WorkspaceScopedViewMixin,
                        mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.DestroyModelMixin,
                        viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        # We also filter by workspace if provided, or just all notifications for this user
        wid = self.get_workspace_id(self.request)
        qs = Notification.objects.filter(user=self.request.user)
        if wid:
            qs = qs.filter(data__workspace_id=wid)
        return qs

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({"status": "notification marked as read"})

    @action(detail=False, methods=["post"])
    def mark_all_as_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"status": "all notifications marked as read"})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread_count": count})


class NotificationPreferenceViewSet(WorkspaceScopedViewMixin,
                                      viewsets.ModelViewSet):
    """
    ViewSet for managing workspace notification settings.
    GET /v1/notifications/preferences/?workspace_id=...
    PATCH /v1/notifications/preferences/<id>/
    """
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsWorkspaceAdmin]

    def get_queryset(self):
        wid = self.get_workspace_id(self.request)
        if not wid:
            return NotificationPreference.objects.none()
        return NotificationPreference.objects.filter(workspace_id=wid)

    def perform_create(self, serializer):
        wid = self.get_workspace_id(self.request)
        serializer.save(workspace_id=wid)
