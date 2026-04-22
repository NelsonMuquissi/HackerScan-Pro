from django.urls import path
from . import views

urlpatterns = [
    path('findings/<uuid:finding_id>/explain/', views.AIExplanationView.as_view(), name='ai-explain'),
    path('findings/<uuid:finding_id>/remediate/', views.AIRemediationView.as_view(), name='ai-remediate'),
    path('scans/<uuid:scan_id>/prediction/', views.AIScanPredictionView.as_view(), name='ai-scan-prediction'),
]
