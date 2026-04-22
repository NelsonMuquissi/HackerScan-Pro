"""
HackScan Pro — User & Auth views.
Refactored to be pure Django Views, based on BaseView for standard behavior.
"""
from django.utils.decorators import method_decorator
from pydantic import ValidationError

from .auth_flow import UserRegistrationSchema, UserLoginSchema, AuthServiceFlow
from .decorators import jwt_required
from .serializers import (
    APIKeyCreateSerializer,
    APIKeyListSerializer,
    APIKeyResponseSerializer,
    ChangePasswordSerializer,
    TOTPDisableSerializer,
    TOTPSetupResponseSerializer,
    TOTPVerifySerializer,
    UserMeSerializer,
    UserProfileSerializer,
    UserUpdateSerializer,
)
from .services import APIKeyService, AuthService, TwoFactorService, UserService
from .views_base import BaseView


def _get_client_ip(request) -> str:
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


# ─── Auth ─────────────────────────────────────────────────────────────────────

class AuthRegisterView(BaseView):
    """POST /v1/auth/register/"""

    def post(self, request):
        try:
            schema = UserRegistrationSchema(**self.json_body)
        except ValidationError as e:
            return self.error_response(
                message="Validation failed.",
                code="validation_error",
                detail=e.errors(),
                status=400
            )
        
        UserService.register(email=schema.email, password=schema.password, full_name=schema.full_name)
        return self.success_response(
            {"message": "Account created. Please check your email to verify your account."},
            status=201,
        )


class AuthVerifyEmailView(BaseView):
    """GET /v1/auth/verify-email/?token=<jwt>"""

    def get(self, request):
        token = request.GET.get("token", "")
        user, tokens = UserService.verify_email(token)
        return self.success_response({"message": "Email verified successfully.", **tokens})


class AuthLoginView(BaseView):
    """POST /v1/auth/login/"""

    def post(self, request):
        try:
            schema = UserLoginSchema(**self.json_body)
        except ValidationError as e:
            return self.error_response(
                message="Validation failed.",
                code="validation_error",
                detail=e.errors(),
                status=400
            )
            
        tokens = AuthService.login(
            email=schema.email,
            password=schema.password,
            totp_code=self.json_body.get("totp_code", ""),
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        return self.success_response(tokens)


@method_decorator(jwt_required, name='dispatch')
class AuthLogoutView(BaseView):
    """POST /v1/auth/logout/ — blacklists the refresh token."""

    def post(self, request):
        # We manually process JWT tokens so blacklist would need a custom implementation
        # (e.g. saving invalid tokens to a cache). For now, just return 204.
        return self.success_response(status=204)


class AuthRefreshView(BaseView):
    """POST /v1/auth/refresh/"""

    def post(self, request):
        refresh_token = self.json_body.get("refresh")
        if not refresh_token:
            return self.error_response("Refresh token is required", code="validation_error", status=400)
        
        try:
            payload = AuthServiceFlow.verify_token(refresh_token, token_type="refresh")
            user_id = payload.get("user_id")
            if not user_id:
                raise ValueError("Invalid token payload")
        except ValueError as e:
            return self.error_response(str(e), code="authentication_failed", status=401)
            
        token_response = AuthServiceFlow.create_token_pair({"user_id": user_id})
        return self.success_response({
            "access": token_response.access_token,
            "refresh": token_response.refresh_token
        })


@method_decorator(jwt_required, name='dispatch')
class AuthPasswordChangeView(BaseView):
    """POST /v1/auth/password/change/"""

    def post(self, request):
        serializer = ChangePasswordSerializer(data=self.json_body)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        AuthService.change_password(
            user=request.user,
            old_password=d["old_password"],
            new_password=d["new_password"],
        )
        return self.success_response({"message": "Password changed successfully."})


# ─── Me ───────────────────────────────────────────────────────────────────────

@method_decorator(jwt_required, name='dispatch')
class MeView(BaseView):
    """GET /v1/users/me/  |  PATCH /v1/users/me/"""

    def get(self, request):
        serializer = UserMeSerializer(request.user)
        return self.success_response(serializer.data)

    def patch(self, request):
        serializer = UserUpdateSerializer(data=self.json_body)
        serializer.is_valid(raise_exception=True)
        user = UserService.update_profile(request.user, **serializer.validated_data)
        return self.success_response(UserMeSerializer(user).data)


@method_decorator(jwt_required, name='dispatch')
class ProfileView(BaseView):
    """GET /v1/users/me/profile/  |  PATCH /v1/users/me/profile/"""

    def get(self, request):
        profile, _ = request.user.profile.__class__.objects.get_or_create(user=request.user)
        return self.success_response(UserProfileSerializer(profile).data)

    def patch(self, request):
        profile = UserService.update_user_profile(request.user, self.json_body)
        return self.success_response(UserProfileSerializer(profile).data)


# ─── 2FA ──────────────────────────────────────────────────────────────────────

@method_decorator(jwt_required, name='dispatch')
class TOTPSetupView(BaseView):
    """POST /v1/users/me/2fa/setup/  — generates secret + otpauth URL."""

    def post(self, request):
        data = TwoFactorService.generate_setup(request.user)
        return self.success_response(TOTPSetupResponseSerializer(data).data)


@method_decorator(jwt_required, name='dispatch')
class TOTPVerifyView(BaseView):
    """POST /v1/users/me/2fa/verify/  — verifies code and enables 2FA."""

    def post(self, request):
        serializer = TOTPVerifySerializer(data=self.json_body)
        serializer.is_valid(raise_exception=True)
        backup_codes = TwoFactorService.verify_and_enable(
            user=request.user, code=serializer.validated_data["code"]
        )
        return self.success_response({"message": "2FA enabled.", "backup_codes": backup_codes})


@method_decorator(jwt_required, name='dispatch')
class TOTPDisableView(BaseView):
    """DELETE /v1/users/me/2fa/  — disables 2FA."""

    def delete(self, request):
        serializer = TOTPDisableSerializer(data=self.json_body)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        TwoFactorService.disable(
            user=request.user,
            password=d["password"],
            code=d.get("code", ""),
        )
        return self.success_response({"message": "2FA disabled."})


# ─── API Keys ─────────────────────────────────────────────────────────────────

@method_decorator(jwt_required, name='dispatch')
class APIKeyListCreateView(BaseView):
    """GET /v1/users/me/api-keys/  |  POST /v1/users/me/api-keys/"""

    def get(self, request):
        keys = APIKeyService.list_for_user(request.user)
        return self.success_response(APIKeyListSerializer(keys, many=True).data)

    def post(self, request):
        serializer = APIKeyCreateSerializer(data=self.json_body)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        instance, raw_key = APIKeyService.create(
            user=request.user,
            name=d["name"],
            scopes=d.get("scopes", []),
            expires_at=d.get("expires_at"),
        )
        response_data = APIKeyResponseSerializer(instance).data
        response_data["key"] = raw_key  # Only time the raw key is exposed
        return self.success_response(response_data, status=201)


@method_decorator(jwt_required, name='dispatch')
class APIKeyRevokeView(BaseView):
    """DELETE /v1/users/me/api-keys/<key_id>/"""

    def delete(self, request, key_id):
        APIKeyService.revoke(user=request.user, key_id=key_id)
        return self.success_response(status=204)


# ─── Workspace & Team ─────────────────────────────────────────────────────────

from .serializers import WorkspaceMemberSerializer, WorkspaceInviteSerializer, AuditLogSerializer
from .models import Workspace

@method_decorator(jwt_required, name='dispatch')
class WorkspaceMemberListView(BaseView):
    """GET /v1/workspaces/<id>/members/"""

    def get(self, request, workspace_id):
        # TODO: verify user belongs to workspace
        members = WorkspaceService.list_members(workspace_id)
        return self.success_response(WorkspaceMemberSerializer(members, many=True).data)


@method_decorator(jwt_required, name='dispatch')
class WorkspaceInviteView(BaseView):
    """POST /v1/workspaces/<id>/invites/ | GET /v1/workspaces/join/<token>/"""

    def post(self, request, workspace_id):
        workspace = Workspace.objects.get(pk=workspace_id)
        # TODO: Permission check (only owner/admin can invite)
        
        email = self.json_body.get("email")
        role = self.json_body.get("role", "member")
        
        if not email:
            return self.error_response("Email is required.", status=400)
            
        invite = WorkspaceService.invite_user(
            workspace=workspace,
            invited_by=request.user,
            email=email,
            role=role
        )
        return self.success_response(WorkspaceInviteSerializer(invite).data, status=201)


@method_decorator(jwt_required, name='dispatch')
class WorkspaceInviteAcceptView(BaseView):
    """POST /v1/workspaces/join/"""

    def post(self, request):
        token = self.json_body.get("token")
        if not token:
            return self.error_response("Token is required.", status=400)
            
        member = WorkspaceService.accept_invite(user=request.user, token=token)
        return self.success_response(WorkspaceMemberSerializer(member).data)


@method_decorator(jwt_required, name='dispatch')
class AuditLogListView(BaseView):
    """GET /v1/workspaces/<id>/audit-logs/"""

    def get(self, request, workspace_id):
        logs = WorkspaceService.get_audit_logs(workspace_id)
        return self.success_response(AuditLogSerializer(logs, many=True).data)
