"""Workspace endpoints — /v1/workspaces/"""
from django.urls import path
from .views import (
    WorkspaceMemberListView,
    WorkspaceInviteView,
    WorkspaceInviteAcceptView,
    AuditLogListView,
)

urlpatterns = [
    path("<uuid:workspace_id>/members/", WorkspaceMemberListView.as_view(), name="workspace-members"),
    path("<uuid:workspace_id>/invites/", WorkspaceInviteView.as_view(), name="workspace-invites"),
    path("<uuid:workspace_id>/audit-logs/", AuditLogListView.as_view(), name="workspace-audit-logs"),
    path("join/", WorkspaceInviteAcceptView.as_view(), name="workspace-join"),
]
