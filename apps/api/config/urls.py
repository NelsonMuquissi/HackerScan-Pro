"""
Root URL configuration for HackScan Pro API.
"""
from django.urls import path, include
from core import views as core_views
from core.metrics import metrics_view

urlpatterns = [
    # ── Observability (unauthenticated) ──────────────────────────
    path("health/", core_views.health_liveness, name="health-liveness"),
    path("health/ready/", core_views.health_readiness, name="health-readiness"),
    path("metrics/", metrics_view, name="prometheus-metrics"),

    # ── API v1 ───────────────────────────────────────────────────
    path("v1/auth/",  include("users.urls")),
    path("v1/users/", include("users.urls_me")),
    path("v1/scans/", include("scans.urls")),
    path("v1/billing/", include("billing.urls")),
    path("v1/reports/", include("reports.urls")),
    path("v1/ai/", include("ai.urls")),
    path("v1/notifications/", include("notifications.urls")),
    path("v1/integrations/", include("integrations.urls")),
    path("v1/bounty/", include("bounty.urls")),
    path("v1/marketplace/", include("marketplace.urls")),
    path("v1/workspaces/", include("users.urls_workspaces")),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
