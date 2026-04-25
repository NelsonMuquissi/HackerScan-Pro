"""
HackScan Pro — User business logic services.

Each service class is stateless (all @staticmethod / @classmethod).
Views must not contain business logic; they delegate here.
"""
import hashlib
import secrets
from typing import Optional

import pyotp
from django.contrib.auth.hashers import check_password
from django.core.mail import send_mail
from django.conf import settings
from .auth_flow import PasswordService, AuthServiceFlow

from core.exceptions import (
    AuthenticationError,
    ConflictError,
    ServiceError,
    TwoFactorRequiredError,
)
from .models import APIKey, AuditLog, RefreshToken, User, UserProfile, Workspace, WorkspaceMember, WorkspaceInvite


# ─── UserService ─────────────────────────────────────────────────────────────

class UserService:
    """Handles registration, email verification, and profile management."""

    @staticmethod
    def register(email: str, password: str, full_name: str) -> User:
        """
        Step 1–5 of the registration flow:
          - Create user with hashed password
          - In DEBUG mode: auto-verify + bootstrap workspace (no email needed)
          - In production: send verification email
          - Return user (no tokens yet)
        """
        from django.conf import settings as django_settings  # noqa: PLC0415

        if User.objects.filter(email__iexact=email).exists():
            raise ConflictError("An account with this email already exists.")

        # In dev mode, auto-verify so users can log in immediately
        auto_verify = getattr(django_settings, "DEBUG", False)

        # Use PasswordService from auth_flow for bcrypt hashing
        hashed_pw = PasswordService.hash_password(password)
        user = User.objects.create(
            email=email.lower(),
            password=hashed_pw,
            full_name=full_name,
            email_verified=auto_verify,
            is_active=True,
        )

        if auto_verify:
            # Bootstrap workspace + membership (same as verify_email)
            workspace, _ = Workspace.objects.get_or_create(
                slug=f"personal-{user.id}",
                defaults={"owner": user, "name": f"{full_name or email}'s Workspace"},
            )
            WorkspaceMember.objects.get_or_create(
                workspace=workspace, user=user, defaults={"role": "owner"}
            )
        else:
            UserService._send_verification_email(user)

        AuditLog.log(action="user.registered", user=user)
        return user

    @staticmethod
    def verify_email(token: str) -> tuple[User, dict]:
        """
        Step 6–8: decode JWT verification token, activate user,
        bootstrap workspace + free plan, return token pair.
        """
        try:
            payload = AuthServiceFlow.verify_token(token, token_type="email_verify")
            user_id = payload.get("user_id")
            purpose = payload.get("purpose")
        except ValueError:
            raise AuthenticationError("Invalid or expired verification link.")

        if purpose != "email_verify":
            raise AuthenticationError("Invalid token purpose.")

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise AuthenticationError("User not found.")

        if user.email_verified:
            raise ConflictError("Email is already verified.")

        user.email_verified = True
        user.save(update_fields=["email_verified"])

        # Bootstrap personal workspace
        workspace, _ = Workspace.objects.get_or_create(
            slug=f"personal-{user.id}",
            defaults={"owner": user, "name": f"{user.full_name or user.email}'s Workspace"},
        )
        WorkspaceMember.objects.get_or_create(
            workspace=workspace, user=user, defaults={"role": "owner"}
        )

        AuditLog.log(action="user.email_verified", user=user)
        return user, AuthService._issue_tokens(user)

    @staticmethod
    def _send_verification_email(user: User) -> None:
        """Issues a short-lived JWT and mails the verification link."""
        # Issue a verification token manually utilizing AuthServiceFlow secret
        import jwt
        from .auth_flow import SECRET_KEY, ALGORITHM
        from datetime import datetime, timedelta

        expire = datetime.utcnow() + timedelta(hours=24)
        token_payload = {
            "user_id": str(user.id),
            "purpose": "email_verify",
            "type": "email_verify",
            "exp": expire
        }
        token_str = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)

        verify_url = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/verify-email?token={token_str}"

        send_mail(
            subject="Confirma o teu email — HackScan Pro",
            message=f"Olá {user.full_name or user.email}!\n\nClica no link para activar a tua conta:\n{verify_url}\n\nO link expira em 24 horas.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

    @staticmethod
    def update_profile(user: User, full_name: str | None = None, avatar_url: str | None = None) -> User:
        update_fields = []
        if full_name is not None:
            user.full_name = full_name
            update_fields.append("full_name")
        if avatar_url is not None:
            user.avatar_url = avatar_url
            update_fields.append("avatar_url")
        if update_fields:
            user.save(update_fields=update_fields)
        return user

    @staticmethod
    def update_user_profile(user: User, data: dict) -> UserProfile:
        profile, _ = UserProfile.objects.get_or_create(user=user)
        allowed = ["company", "country", "timezone", "language", "notification_settings"]
        update_fields = []
        for field in allowed:
            if field in data:
                setattr(profile, field, data[field])
                update_fields.append(field)
        if update_fields:
            profile.save(update_fields=update_fields)
        return profile


# ─── AuthService ─────────────────────────────────────────────────────────────

class AuthService:
    """Handles login, logout, token refresh, and password changes."""

    @staticmethod
    def login(email: str, password: str, totp_code: str = "", ip_address: str = "", user_agent: str = "") -> dict:
        """Authenticates a user and returns a JWT token pair."""
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise AuthenticationError("Invalid credentials.")

        if not user.is_active:
            raise AuthenticationError("This account is deactivated.")

        if not PasswordService.verify_password(password, user.password):
            AuditLog.log(action="user.login_failed", user=user, ip_address=ip_address)
            raise AuthenticationError("Invalid credentials.")

        if not user.email_verified:
            raise ServiceError("Please verify your email before logging in.")

        # 2FA check
        if user.totp_enabled:
            if not totp_code:
                raise TwoFactorRequiredError()
            if not TwoFactorService.verify_code(user, totp_code):
                AuditLog.log(action="user.login_2fa_failed", user=user, ip_address=ip_address)
                raise AuthenticationError("Invalid 2FA code.")

        # Update last login
        from django.utils import timezone  # noqa: PLC0415
        user.last_login_at = timezone.now()
        user.last_login_ip = ip_address or None
        user.save(update_fields=["last_login_at", "last_login_ip"])

        # Include primary workspace in the log if available
        workspace = user.owned_workspaces.filter(is_active=True).first()
        if not workspace:
            membership = user.memberships.select_related("workspace").filter(workspace__is_active=True).first()
            if membership:
                workspace = membership.workspace

        AuditLog.log(
            action="user.login",
            user=user,
            workspace=workspace,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return AuthService._issue_tokens(user)

    @staticmethod
    def _issue_tokens(user: User) -> dict:
        token_response = AuthServiceFlow.create_token_pair({"user_id": str(user.id)})
        return {
            "access": token_response.access_token,
            "refresh": token_response.refresh_token,
        }

    @staticmethod
    def change_password(user: User, old_password: str, new_password: str) -> None:
        if not PasswordService.verify_password(old_password, user.password):
            raise AuthenticationError("Current password is incorrect.")
        user.password = PasswordService.hash_password(new_password)
        user.save(update_fields=["password"])
        AuditLog.log(action="user.password_changed", user=user)


# ─── TwoFactorService ────────────────────────────────────────────────────────

class TwoFactorService:
    """Manages TOTP 2FA lifecycle as specified in section 7.1 of the master doc."""

    @staticmethod
    def generate_setup(user: User) -> dict:
        """
        Generates a fresh TOTP secret, persists it (unverified),
        and returns the secret + provisioning URL for QR rendering.
        The secret must be confirmed via `verify_and_enable()` before 2FA is active.
        """
        secret = pyotp.random_base32()
        # Store temporarily — totp_enabled remains False until verified
        user.totp_secret = secret
        user.save(update_fields=["totp_secret"])

        otpauth_url = pyotp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name="HackScan Pro",
        )
        return {"secret": secret, "otpauth_url": otpauth_url}

    @staticmethod
    def verify_code(user: User, code: str) -> bool:
        """Validates a TOTP code, tolerating ±1 time window (±30 s)."""
        if not user.totp_secret:
            return False
        return pyotp.TOTP(user.totp_secret).verify(code, valid_window=1)

    @staticmethod
    def verify_and_enable(user: User, code: str) -> list[str]:
        """
        Verifies the code against the pending secret, activates 2FA,
        and returns one-time backup codes.
        """
        if not TwoFactorService.verify_code(user, code):
            raise ServiceError("Invalid TOTP code.")

        backup_codes = TwoFactorService._generate_backup_codes()
        user.totp_enabled = True
        user.save(update_fields=["totp_enabled"])

        AuditLog.log(action="user.2fa_enabled", user=user)
        return backup_codes

    @staticmethod
    def disable(user: User, password: str, code: str = "") -> None:
        """Disables 2FA after re-authenticating with password (+ TOTP code if active)."""
        if not PasswordService.verify_password(password, user.password):
            raise AuthenticationError("Current password is incorrect.")
        if user.totp_enabled and code:
            if not TwoFactorService.verify_code(user, code):
                raise AuthenticationError("Invalid TOTP code.")

        user.totp_enabled = False
        user.totp_secret = None
        user.save(update_fields=["totp_enabled", "totp_secret"])
        AuditLog.log(action="user.2fa_disabled", user=user)

    @staticmethod
    def _generate_backup_codes(count: int = 8) -> list[str]:
        """Returns a list of uppercase hex backup codes."""
        return [secrets.token_hex(4).upper() for _ in range(count)]


# ─── APIKeyService ───────────────────────────────────────────────────────────

class APIKeyService:
    """CRUD for API keys."""

    @staticmethod
    def create(user: User, name: str, scopes: list[str], expires_at=None) -> tuple[APIKey, str]:
        # Resolve workspace
        workspace = user.owned_workspaces.filter(is_active=True).first()
        if not workspace:
            membership = user.memberships.select_related("workspace").filter(workspace__is_active=True).first()
            if membership:
                workspace = membership.workspace

        instance, raw_key = APIKey.generate(
            user=user, 
            workspace=workspace,
            name=name, 
            scopes=scopes, 
            expires_at=expires_at
        )
        AuditLog.log(
            action="api_key.created", 
            user=user, 
            workspace=workspace,
            resource_type="APIKey", 
            resource_id=instance.id
        )
        return instance, raw_key

    @staticmethod
    def revoke(user: User, key_id: str) -> None:
        key = APIKey.objects.filter(pk=key_id, user=user, is_active=True).first()
        if not key:
            from core.exceptions import NotFoundError  # noqa: PLC0415
            raise NotFoundError("API key not found.")
        key.is_active = False
        key.save(update_fields=["is_active"])
        AuditLog.log(
            action="api_key.revoked", 
            user=user, 
            workspace=key.workspace,
            resource_type="APIKey", 
            resource_id=key.id
        )

    @staticmethod
    def list_for_user(user: User):
        return APIKey.objects.filter(user=user, is_active=True).order_by("-created_at")


# ─── WorkspaceService ────────────────────────────────────────────────────────

from django.utils import timezone
from datetime import timedelta

class WorkspaceService:
    """Handles workspace members, invitations and audit logs."""

    @staticmethod
    def list_members(workspace_id: str):
        return WorkspaceMember.objects.filter(workspace_id=workspace_id).select_related("user")

    @staticmethod
    def invite_user(workspace: Workspace, invited_by: User, email: str, role: str) -> WorkspaceInvite:
        # Check for existing pending invite
        existing = WorkspaceInvite.objects.filter(
            workspace=workspace, email=email, status="PENDING"
        ).first()
        if existing:
            if existing.expires_at > timezone.now():
                return existing
            existing.status = "EXPIRED"
            existing.save()

        invite = WorkspaceInvite.objects.create(
            workspace=workspace,
            invited_by=invited_by,
            email=email.lower(),
            role=role,
            token=WorkspaceInvite.generate_token(),
            expires_at=timezone.now() + timedelta(days=7),
            status="PENDING"
        )
        
        # In a real app, we would send an email here.
        # send_mail(...)
        
        AuditLog.log(
            action="workspace.user_invited",
            user=invited_by,
            workspace=workspace,
            resource_type="Workspace",
            resource_id=workspace.id,
            metadata={"invite_id": str(invite.id), "email": email}
        )
        return invite

    @staticmethod
    def accept_invite(user: User, token: str) -> WorkspaceMember:
        invite = WorkspaceInvite.objects.filter(token=token, status="PENDING").first()
        if not invite or not invite.is_valid:
            raise ServiceError("Invalid or expired invite.")
        
        # Check if already a member
        if WorkspaceMember.objects.filter(workspace=invite.workspace, user=user).exists():
            invite.status = "ACCEPTED"
            invite.save()
            return WorkspaceMember.objects.get(workspace=invite.workspace, user=user)

        member = WorkspaceMember.objects.create(
            workspace=invite.workspace,
            user=user,
            role=invite.role
        )
        
        invite.status = "ACCEPTED"
        invite.accepted_at = timezone.now()
        invite.save()

        AuditLog.log(
            action="workspace.invite_accepted",
            user=user,
            workspace=invite.workspace,
            resource_type="Workspace",
            resource_id=invite.workspace.id
        )
        return member

    @staticmethod
    def get_audit_logs(workspace_id: str, limit: int = 100):
        """
        Retrieves logs directly linked to the workspace.
        This is significantly faster than filtering by member IDs.
        """
        return AuditLog.objects.filter(workspace_id=workspace_id).order_by("-created_at")[:limit]

    @staticmethod
    def check_permission(user: User, workspace_id: str, required_role: str = "member") -> bool:
        """
        Utility for Django Views (non-DRF) to verify workspace access.
        """
        from core.permissions import ROLE_HIERARCHY # noqa: PLC0415
        allowed_roles = ROLE_HIERARCHY.get(required_role, [])
        return WorkspaceMember.objects.filter(
            workspace_id=workspace_id,
            user=user,
            role__in=allowed_roles
        ).exists()
