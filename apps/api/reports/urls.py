from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.ReportViewSet, basename='report')

urlpatterns = [
    path('scans/<uuid:scan_id>/report/', views.ReportCreateView.as_view(), name='report-create'),
    path('verify/', views.ReportVerificationView.as_view(), name='report-verify'),
    path('', include(router.urls)),
]
