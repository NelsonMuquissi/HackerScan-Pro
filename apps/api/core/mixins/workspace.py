from uuid import UUID

class WorkspaceScopedViewMixin:
    """Helper methods for resolving workspace from request."""
    def get_workspace_id(self, request):
        # 1. Check URL kwargs
        # 2. Check query params
        # 3. Check request data
        wid = (
            getattr(self, 'kwargs', {}).get("workspace_id")
            or request.query_params.get("workspace_id")
            or request.data.get("workspace_id")
        )
        if wid and wid != "undefined":
            return str(wid)
            
        # Fallback to the user's primary owned workspace
        owned = request.user.owned_workspaces.first()
        if owned:
            return str(owned.id)
            
        # Fallback to any workspace membership
        membership = request.user.memberships.first()
        if membership:
            return str(membership.workspace_id)
            
        return None
