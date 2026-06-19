from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from django.db.models import Count
from .views_base import BaseView
from .decorators import superadmin_required
from .serializers import GlobalAdminUserSerializer
from .models import Workspace, AuditLog
from scans.models import Scan
from scans.models import Finding

User = get_user_model()

@method_decorator(superadmin_required, name='dispatch')
class GlobalAdminUserListView(BaseView):
    """GET /v1/admin/users/ — list all platform users."""
    
    def get(self, request):
        users = User.objects.all().order_by("-created_at")
        serializer = GlobalAdminUserSerializer(users, many=True)
        return self.success_response(serializer.data)

@method_decorator(superadmin_required, name='dispatch')
class GlobalAdminUserDetailView(BaseView):
    """
    GET /v1/admin/users/<id>/ — get user details.
    PATCH /v1/admin/users/<id>/ — update user role/status.
    """
    
    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return self.error_response("User not found.", status=404)
        
        serializer = GlobalAdminUserSerializer(user)
        return self.success_response(serializer.data)

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return self.error_response("User not found.", status=404)

        # Basic role validation
        allowed_roles = ["user", "admin", "superadmin"]
        new_role = self.json_body.get("role")
        if new_role and new_role not in allowed_roles:
            return self.error_response(f"Invalid role. Must be one of {allowed_roles}", status=400)

        # Perform update
        serializer = GlobalAdminUserSerializer(user, data=self.json_body, partial=True)
        if serializer.is_valid():
            serializer.save()
            return self.success_response(serializer.data)
        return self.error_response("Invalid data.", detail=serializer.errors)

@method_decorator(superadmin_required, name='dispatch')
class GlobalAdminStatsView(BaseView):
    """GET /v1/admin/stats/ — Platform-wide statistics."""
    
    def get(self, request):
        # Use cached integrity check result
        from django.core.cache import cache
        integrity_cache = cache.get("audit_log_integrity_status")
        audit_status = integrity_cache.get("status", "SECURE") if integrity_cache else "SECURE"
        
        stats = {
            "total_users": User.objects.count(),
            "total_workspaces": Workspace.objects.filter(is_active=True).count(),
            "total_scans": Scan.objects.count(),
            "total_findings": Finding.objects.count(),
            "active_users_24h": User.objects.filter(last_login_at__gte=timezone_now_minus_24h()).count(),
            "audit_log_integrity": audit_status,
        }
        return self.success_response(stats)

def timezone_now_minus_24h():
    from django.utils import timezone
    from datetime import timedelta
    return timezone.now() - timedelta(hours=24)
