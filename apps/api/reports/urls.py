from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.ReportViewSet, basename='report')

urlpatterns = [
    path('scans/<uuid:scan_id>/report/', views.ReportCreateView.as_view(), name='report-create'),
    path('', include(router.urls)),
]
