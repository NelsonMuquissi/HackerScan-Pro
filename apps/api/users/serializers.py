"""
HackScan Pro — User serializers.
Handles validation, serialization and deserialization for all user-related endpoints.
"""
import re

from django.contrib.auth.hashers import check_password
from rest_framework import serializers

from .models import User, UserProfile, APIKey


# ─── Password validation ──────────────────────────────────────────────────────

_PASSWORD_PATTERN = re.compile(
    r"^(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]).{12,}$"
)


def validate_password_strength(value: str) -> str:
    """
    Min 12 chars, at least 1 uppercase, 1 digit, 1 special character.
    Matches the spec in section 7.1.
    """
    if not _PASSWORD_PATTERN.match(value):
        raise serializers.ValidationError(
            "Password must be at least 12 characters and include "
            "1 uppercase letter, 1 number, and 1 special character."
        )
    return value


# ─── Registration / Auth ─────────────────────────────────────────────────────



class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(
        write_only=True,
        min_length=12,
        style={"input_type": "password"},
        validators=[validate_password_strength],
    )
    confirm_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data


# ─── User / Profile ──────────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    """General representation of a user."""
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "avatar_url", "role"]
        read_only_fields = fields


class UserMeSerializer(serializers.ModelSerializer):
    """Public representation of the authenticated user — no sensitive fields."""
    subscription_plan = serializers.SerializerMethodField()
    workspace_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "full_name", "avatar_url",
            "role", "email_verified", "totp_enabled",
            "last_login_at", "created_at",
            "subscription_plan", "workspace_id",
        ]
        read_only_fields = fields

    def get_workspace_id(self, obj):
        # Return the first active workspace ID
        membership = obj.memberships.select_related('workspace').filter(workspace__is_active=True).first()
        if membership:
            return membership.workspace.id
        workspace = obj.owned_workspaces.filter(is_active=True).first()
        return workspace.id if workspace else None

    def get_subscription_plan(self, obj):
        # 1. Check if user owns an active workspace
        owned_workspace = obj.owned_workspaces.filter(is_active=True).first()
        if owned_workspace:
            return owned_workspace.plan
            
        # 2. Check if user is a member of an active workspace
        membership = obj.memberships.select_related('workspace').filter(workspace__is_active=True).first()
        if membership:
            return membership.workspace.plan
            
        # 3. Fallback
        return "free"


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["full_name", "avatar_url"]


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "company", "country", "timezone",
            "language", "notification_settings",
        ]


# ─── API Keys ─────────────────────────────────────────────────────────────────

class APIKeyCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    scopes = serializers.ListField(
        child=serializers.CharField(),
        default=list,
        help_text='e.g. ["scans:read", "scans:write"]',
    )
    expires_at = serializers.DateTimeField(required=False, allow_null=True)


class APIKeyResponseSerializer(serializers.ModelSerializer):
    """Used for listing keys — never exposes the raw key or hash."""
    key = serializers.CharField(read_only=True, help_text="Shown once at creation only.")

    class Meta:
        model = APIKey
        fields = [
            "id", "name", "key_prefix", "scopes",
            "last_used_at", "expires_at", "is_active", "created_at",
            "key",  # only populated in the create response
        ]
        read_only_fields = fields


class APIKeyListSerializer(serializers.ModelSerializer):
    """Safe listing — no key field."""

    class Meta:
        model = APIKey
        fields = [
            "id", "name", "key_prefix", "scopes",
            "last_used_at", "expires_at", "is_active", "created_at",
        ]
        read_only_fields = fields


# ─── 2FA ─────────────────────────────────────────────────────────────────────

class TOTPSetupResponseSerializer(serializers.Serializer):
    secret = serializers.CharField(read_only=True)
    otpauth_url = serializers.CharField(read_only=True)


class TOTPVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=8, min_length=6)


class TOTPDisableSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    code = serializers.CharField(max_length=8, min_length=6, required=False)


# ─── Workspace & Team ─────────────────────────────────────────────────────────

from .models import WorkspaceMember, WorkspaceInvite

class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = ["id", "user_email", "user_name", "role", "joined_at"]
        read_only_fields = fields


class WorkspaceInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceInvite
        fields = ["id", "email", "role", "status", "expires_at", "created_at"]
        read_only_fields = ["id", "status", "expires_at", "created_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True, default="System")

    class Meta:
        from .models import AuditLog
        model = AuditLog
        fields = [
            "id", "action", "user_email", "resource_type", 
            "resource_id", "ip_address", "created_at", "metadata"
        ]
        read_only_fields = fields
