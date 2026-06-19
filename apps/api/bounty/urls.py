from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PublicProgramViewSet, 
    WorkspaceBountyViewSet, 
    WorkspaceSubmissionViewSet,
    ResearcherSubmissionViewSet,
    TransparencyLogView,
    TransparencyLogExportView
)

router = DefaultRouter()
router.register(r'programs', PublicProgramViewSet, basename='bounty-programs')
router.register(r'workspace-management', WorkspaceBountyViewSet, basename='bounty-workspace')
router.register(r'workspace-submissions', WorkspaceSubmissionViewSet, basename='bounty-workspace-submissions')
router.register(r'submissions', ResearcherSubmissionViewSet, basename='bounty-submissions')

urlpatterns = [
    path('transparency-log/', TransparencyLogView.as_view(), name='bounty-transparency-log'),
    path('transparency-log/export/', TransparencyLogExportView.as_view(), name='bounty-transparency-log-export'),
    path('', include(router.urls)),
]
