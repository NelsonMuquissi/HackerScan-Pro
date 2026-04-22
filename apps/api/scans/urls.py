"""URL configuration for the scans app."""
from django.urls import path
from . import views

urlpatterns = [
    # Scan Targets
    path("targets/",                views.ScanTargetListCreateView.as_view(), name="scan-target-list"),
    path("targets/<uuid:target_id>/", views.ScanTargetDetailView.as_view(),  name="scan-target-detail"),

    # Scans
    path("",                        views.ScanListCreateView.as_view(),       name="scan-list"),
    path("<uuid:scan_id>/",         views.ScanDetailView.as_view(),           name="scan-detail"),
    path("<uuid:scan_id>/start/",   views.ScanStartView.as_view(),            name="scan-start"),
    path("<uuid:scan_id>/cancel/",  views.ScanCancelView.as_view(),           name="scan-cancel"),
    path("<uuid:scan_id>/findings/",views.ScanFindingsView.as_view(),         name="scan-findings"),

    # Scheduling
    path("schedules/",              views.ScheduledScanListCreateView.as_view(), name="scan-schedule-list"),
    path("schedules/<uuid:schedule_id>/", views.ScheduledScanDetailView.as_view(), name="scan-schedule-detail"),

    # Plugin registry
    path("plugins/",                views.ScanPluginListView.as_view(),       name="scan-plugin-list"),

    # Quick Scan (one-step convenience)
    path("quick/",                  views.QuickScanView.as_view(),            name="scan-quick"),

    # Dashboard Stats
    path("dashboard/",              views.DashboardStatsView.as_view(),       name="scan-dashboard"),
]
