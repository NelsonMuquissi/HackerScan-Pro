"""
RBAC permission classes for HackScan Pro.
Workspace-scoped role hierarchy: viewer < member < admin < owner
"""
from rest_framework.permissions import BasePermission, IsAuthenticated


ROLE_HIERARCHY: dict[str, list[str]] = {
    "viewer": ["viewer", "member", "admin", "owner"],
    "member": ["member", "admin", "owner"],
    "admin": ["admin", "owner"],
    "owner": ["owner"],
}


class WorkspacePermission(BasePermission):
    """
    Verifica se o utilizador autenticado tem pelo menos a 'required_role'
    no workspace referenciado na request.

    Uso típico:
        class MyView(APIView):
            permission_classes = [IsAuthenticated, IsWorkspaceAdmin]
    """

    required_role: str = "member"

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False

        # Global Admin/Superadmin bypass
        if request.user.role in ["admin", "superadmin"]:
            return True

        # Attempt to find workspace_id in common locations
        workspace_id = (
            view.kwargs.get("workspace_id")
            or request.query_params.get("workspace_id")
            or request.data.get("workspace_id")
        )

        if not workspace_id or workspace_id == "undefined":
            # Fallback for list endpoints/lazy requests: try to resolve from user's primary workspace
            # This is consistent with WorkspaceScopedViewMixin fallbacks
            membership = request.user.memberships.first()
            if membership:
                workspace_id = membership.workspace_id
            else:
                return False

        # Internal import to avoid circular dependencies
        from users.models import WorkspaceMember  # noqa: PLC0415

        return WorkspaceMember.objects.filter(
            workspace_id=workspace_id,
            user=request.user,
            role__in=self._get_allowed_roles(),
        ).exists()

    def _get_allowed_roles(self) -> list[str]:
        return ROLE_HIERARCHY.get(self.required_role, [])


class IsWorkspaceMember(WorkspacePermission):
    required_role = "member"


class IsWorkspaceAdmin(WorkspacePermission):
    required_role = "admin"


class IsWorkspaceOwner(WorkspacePermission):
    required_role = "owner"


class IsSuperAdmin(BasePermission):
    """Only platform superadmins."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "superadmin"
        )
