from django.urls import path
from .views_admin import (
    GlobalAdminUserListView,
    GlobalAdminUserDetailView,
    GlobalAdminStatsView,
)
from marketplace.views_admin import GlobalAdminMarketplaceViewSet
from bounty.views_admin import (
    GlobalAdminBountyProgramListView,
    GlobalAdminBountySubmissionListView,
)
from .views_admin_system import (
    GlobalAdminWorkspaceListView,
    GlobalAdminScanListView,
    GlobalAdminAuditLogListView,
    GlobalAdminSystemHealthView,
    GlobalAdminMaintenanceView,
    GlobalAdminCTLogsView,
    GlobalAdminScanPluginViewSet,
)
from core.admin_views import GlobalSettingViewSet

urlpatterns = [
    path("users/", GlobalAdminUserListView.as_view(), name="admin-users-list"),
    path("users/<uuid:pk>/", GlobalAdminUserDetailView.as_view(), name="admin-user-detail"),
    path("stats/", GlobalAdminStatsView.as_view(), name="admin-platform-stats"),
    
    # System Admin
    path("workspaces/", GlobalAdminWorkspaceListView.as_view(), name="admin-workspaces"),
    path("scans/", GlobalAdminScanListView.as_view(), name="admin-scans"),
    path("audit-logs/", GlobalAdminAuditLogListView.as_view(), name="admin-audit-logs"),
    path("system/health/", GlobalAdminSystemHealthView.as_view(), name="admin-system-health"),
    path("system/maintenance/", GlobalAdminMaintenanceView.as_view(), name="admin-system-maintenance"),
    
    # Bounty Admin
    path("bounty/programs/", GlobalAdminBountyProgramListView.as_view(), name="admin-bounty-programs"),
    path("bounty/submissions/", GlobalAdminBountySubmissionListView.as_view(), name="admin-bounty-submissions"),
    
    # Marketplace Admin
    path("marketplace/modules/", GlobalAdminMarketplaceViewSet.as_view({'get': 'list', 'post': 'create'}), name="admin-marketplace-modules"),
    path("marketplace/modules/<uuid:pk>/", GlobalAdminMarketplaceViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}), name="admin-marketplace-module-detail"),
    
    # CT Logs & Strategies Admin
    path("ct-logs/", GlobalAdminCTLogsView.as_view(), name="admin-ct-logs"),
    path("strategies/", GlobalAdminScanPluginViewSet.as_view(), name="admin-strategies-list"),
    path("strategies/<uuid:pk>/", GlobalAdminScanPluginViewSet.as_view(), name="admin-strategies-detail"),
    
    # Global Settings Admin
    path("settings/", GlobalSettingViewSet.as_view({'get': 'list', 'post': 'batch_update'}), name="admin-settings-list"),
    path("settings/by_category/", GlobalSettingViewSet.as_view({'get': 'by_category'}), name="admin-settings-by-category"),
    path("settings/<str:key>/", GlobalSettingViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}), name="admin-settings-detail"),
]
