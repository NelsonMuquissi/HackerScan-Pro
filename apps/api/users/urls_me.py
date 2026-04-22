"""User-self endpoints — /v1/users/me/"""
from django.urls import path
from .views import (
    MeView,
    ProfileView,
    TOTPSetupView,
    TOTPVerifyView,
    TOTPDisableView,
    APIKeyListCreateView,
    APIKeyRevokeView,
)

urlpatterns = [
    path("me/", MeView.as_view(), name="users-me"),
    path("me/profile/", ProfileView.as_view(), name="users-me-profile"),
    path("me/2fa/setup/", TOTPSetupView.as_view(), name="users-2fa-setup"),
    path("me/2fa/verify/", TOTPVerifyView.as_view(), name="users-2fa-verify"),
    path("me/2fa/", TOTPDisableView.as_view(), name="users-2fa-disable"),
    path("me/api-keys/", APIKeyListCreateView.as_view(), name="users-api-keys"),
    path("me/api-keys/<uuid:key_id>/", APIKeyRevokeView.as_view(), name="users-api-key-detail"),
]
