from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PublicProgramViewSet, 
    WorkspaceBountyViewSet, 
    WorkspaceSubmissionViewSet,
    ResearcherSubmissionViewSet
)

router = DefaultRouter()
router.register(r'programs', PublicProgramViewSet, basename='bounty-programs')
router.register(r'workspace-management', WorkspaceBountyViewSet, basename='bounty-workspace')
router.register(r'workspace-submissions', WorkspaceSubmissionViewSet, basename='bounty-workspace-submissions')
router.register(r'submissions', ResearcherSubmissionViewSet, basename='bounty-submissions')

urlpatterns = [
    path('', include(router.urls)),
]
