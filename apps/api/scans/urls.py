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
    path("<uuid:scan_id>/rescan/",  views.ScanRescanView.as_view(),           name="scan-rescan"),
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

    # AI & Feedback
    path("findings/<uuid:finding_id>/analyze-fp/", views.FindingAnalyzeFalsePositiveView.as_view(), name="finding-analyze-fp"),
    path("findings/<uuid:finding_id>/feedback/",   views.FindingFeedbackView.as_view(),           name="finding-feedback"),
    path("findings/<uuid:finding_id>/verify/",     views.FindingVerifyView.as_view(),             name="finding-verify"),
    path("findings/<uuid:finding_id>/poc/",        views.FindingPOCView.as_view(),                name="finding-poc"),
    path("<uuid:scan_id>/risk/",                    views.ScanRiskAssessmentView.as_view(),        name="scan-risk-assessment"),
    path("<uuid:scan_id>/verify-all/",               views.ScanVerifyAllView.as_view(),             name="scan-verify-all"),
    path("evidence-vault/",                         views.EvidenceVaultView.as_view(),            name="evidence-vault"),
    path("evidence-vault/export/",                  views.EvidenceExportVaultView.as_view(),      name="evidence-vault-export"),
    path("evidence-vault/log/",                     views.EvidenceAuditLogView.as_view(),         name="evidence-vault-log"),
]
