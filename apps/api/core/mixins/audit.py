from django.utils import timezone
from users.models import AuditLog, Workspace

class AuditLoggerMixin:
    """
    Mixin for APIViews to provide standardized audit logging.
    Requires WorkspaceScopedViewMixin to be present if workspace-level logging is needed.
    """
    
    def log_audit_action(self, action, resource_type=None, resource_id=None, metadata=None):
        """
        Logs an action with automatic context extraction (IP, UA, Workspace).
        """
        request = getattr(self, 'request', None)
        if not request:
            return None
            
        # Extract workspace if possible
        workspace = None
        if hasattr(self, 'get_workspace_id'):
            wid = self.get_workspace_id(request)
            if wid:
                workspace = Workspace.objects.filter(id=wid).first()
        
        # Log via model method
        return AuditLog.log(
            user=request.user,
            workspace=workspace,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata or {},
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
