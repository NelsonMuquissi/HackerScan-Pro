"""Auth endpoints — /v1/auth/"""
from django.urls import path
from .views import (
    AuthRegisterView,
    AuthVerifyEmailView,
    AuthLoginView,
    AuthLogoutView,
    AuthRefreshView,
    AuthPasswordChangeView,
)

urlpatterns = [
    path("register/", AuthRegisterView.as_view(), name="auth-register"),
    path("verify-email/", AuthVerifyEmailView.as_view(), name="auth-verify-email"),
    path("login/", AuthLoginView.as_view(), name="auth-login"),
    path("logout/", AuthLogoutView.as_view(), name="auth-logout"),
    path("refresh/", AuthRefreshView.as_view(), name="auth-refresh"),
    path("password/change/", AuthPasswordChangeView.as_view(), name="auth-password-change"),
]
