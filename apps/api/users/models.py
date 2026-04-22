"""
HackScan Pro — User & Auth Models.

Tables implemented:
  - User           (custom AbstractBaseUser)
  - UserProfile    (one-to-one extension)
  - WorkspaceMember (for RBAC permission checks)
  - APIKey
  - RefreshToken
  - AuditLog
"""
import hashlib
import secrets
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password
from django.db import models
from django.utils import timezone

from core.models import UUIDModel, TimestampedModel, SoftDeleteModel, SoftDeleteManager


# ─── User ────────────────────────────────────────────────────────────────────

class UserRole(models.TextChoices):
    USER = "user", "User"
    ADMIN = "admin", "Admin"
    SUPERADMIN = "superadmin", "Super Admin"


class UserManager(BaseUserManager):
    """Custom manager — uses email as the unique identifier."""

    def create_user(self, email: str, password: str, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("role", UserRole.SUPERADMIN)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("email_verified", True)
        return self.create_user(email, password, **extra_fields)

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class User(AbstractBaseUser, UUIDModel, TimestampedModel, SoftDeleteModel):
    """
    Platform user — replaces Django's built-in User.
    password_hash is managed by AbstractBaseUser.password (bcrypt via Argon2).
    """
    email = models.EmailField(unique=True, db_index=True)
    email_verified = models.BooleanField(default=False)
    full_name = models.CharField(max_length=255, blank=True, default="")
    avatar_url = models.TextField(blank=True, default="")
    role = models.CharField(
        max_length=50, choices=UserRole.choices, default=UserRole.USER, db_index=True
    )
    is_active = models.BooleanField(default=True)

    # 2FA — secret stored via django-encrypted-fields in production;
    # using TextField here to keep base.txt dependency surface minimal.
    totp_secret = models.TextField(blank=True, null=True, default=None)
    totp_enabled = models.BooleanField(default=False)

    last_login_at = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    objects = UserManager()
    all_objects = models.Manager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["email"],
                condition=models.Q(deleted_at__isnull=True),
                name="idx_users_email_active",
            ),
            models.Index(fields=["created_at"], name="idx_users_created_at"),
        ]

    def __str__(self) -> str:
        return self.email

    # AbstractBaseUser requires is_anonymous / is_authenticated via mixin — inherited.
    # AbstractBaseUser does NOT include is_staff / is_superuser unless AdminMixin added.
    @property
    def is_superadmin(self) -> bool:
        return self.role == UserRole.SUPERADMIN


# ─── UserProfile ─────────────────────────────────────────────────────────────

class UserProfile(UUIDModel, TimestampedModel):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    company = models.CharField(max_length=255, blank=True, default="")
    country = models.CharField(max_length=2, blank=True, default="")  # ISO 3166-1 alpha-2
    timezone = models.CharField(max_length=100, default="UTC")
    language = models.CharField(max_length=10, default="pt")
    notification_settings = models.JSONField(default=dict)

    class Meta:
        db_table = "user_profiles"

    def __str__(self) -> str:
        return f"Profile<{self.user.email}>"


# ─── Workspace (stub — needed by WorkspaceMember FK / RBAC) ──────────────────

class WorkspacePlan(models.TextChoices):
    FREE = "free", "Free"
    PRO = "pro", "Pro"
    TEAM = "team", "Team"
    ENTERPRISE = "enterprise", "Enterprise"


class Workspace(UUIDModel, TimestampedModel, SoftDeleteModel):
    owner = models.ForeignKey(
        User, on_delete=models.RESTRICT, related_name="owned_workspaces"
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)
    plan = models.CharField(
        max_length=50, choices=WorkspacePlan.choices, default=WorkspacePlan.FREE
    )
    logo_url = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    settings = models.JSONField(default=dict)

    class Meta:
        db_table = "workspaces"

    def __str__(self) -> str:
        return self.slug


class WorkspaceMemberRole(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"
    VIEWER = "viewer", "Viewer"


class WorkspaceMember(UUIDModel):
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(
        max_length=50, choices=WorkspaceMemberRole.choices, default=WorkspaceMemberRole.MEMBER
    )
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="invites_sent"
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workspace_members"
        unique_together = [("workspace", "user")]

    def __str__(self) -> str:
        return f"{self.user.email} @ {self.workspace.slug} ({self.role})"


# ─── APIKey ──────────────────────────────────────────────────────────────────

class APIKey(UUIDModel):
    """
    API key for programmatic access.
    The full key is shown only once at creation; only the SHA-256 hash is stored.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    workspace = models.ForeignKey(
        Workspace, on_delete=models.SET_NULL, null=True, blank=True, related_name="api_keys"
    )
    name = models.CharField(max_length=255)
    key_prefix = models.CharField(max_length=8)   # e.g. "hs_live_"
    key_hash = models.CharField(max_length=255, db_index=True)  # SHA-256
    scopes = models.JSONField(default=list)        # ["scans:read", "scans:write"]
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "api_keys"
        indexes = [
            models.Index(
                fields=["key_hash"],
                condition=models.Q(is_active=True),
                name="idx_api_keys_hash_active",
            )
        ]

    def __str__(self) -> str:
        return f"{self.key_prefix}*** ({self.name})"

    @classmethod
    def generate(cls, user: "User", name: str, scopes: list[str], workspace=None, expires_at=None) -> tuple["APIKey", str]:
        """
        Creates a new APIKey and returns (instance, raw_key).
        raw_key is shown to the user once and never stored.
        """
        raw_key = f"hs_live_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        instance = cls.objects.create(
            user=user,
            workspace=workspace,
            name=name,
            key_prefix=raw_key[:8],
            key_hash=key_hash,
            scopes=scopes,
            expires_at=expires_at,
        )
        return instance, raw_key

    @classmethod
    def authenticate(cls, raw_key: str) -> "APIKey | None":
        """Looks up an active, non-expired key by its hash."""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return (
            cls.objects.select_related("user")
            .filter(key_hash=key_hash, is_active=True)
            .filter(
                models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
            )
            .first()
        )


# ─── RefreshToken ────────────────────────────────────────────────────────────

class RefreshToken(UUIDModel):
    """Tracks issued refresh tokens for rotation and revocation."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refresh_tokens")
    token_hash = models.CharField(max_length=255, unique=True)
    device_info = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "refresh_tokens"

    @property
    def is_valid(self) -> bool:
        return self.revoked_at is None and self.expires_at > timezone.now()

    def revoke(self) -> None:
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])


# ─── AuditLog ────────────────────────────────────────────────────────────────

class AuditLog(UUIDModel):
    """Immutable audit trail — never soft-deleted."""
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs"
    )
    action = models.CharField(max_length=100, db_index=True)  # "user.login", "scan.created"
    resource_type = models.CharField(max_length=100, blank=True, default="")
    resource_id = models.UUIDField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_logs"
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_audit_user_created"),
            models.Index(fields=["resource_type", "resource_id"], name="idx_audit_resource"),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} by {self.user_id} at {self.created_at}"

    @classmethod
    def log(
        cls,
        action: str,
        user=None,
        resource_type: str = "",
        resource_id=None,
        ip_address: str | None = None,
        user_agent: str = "",
        metadata: dict | None = None,
    ) -> "AuditLog":
        return cls.objects.create(
            action=action,
            user=user,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {},
        )


# ─── WorkspaceInvite ─────────────────────────────────────────────────────────

class WorkspaceInvite(UUIDModel, TimestampedModel):
    """
    Invitation to join a workspace. 
    Sent via email, contains a unique token.
    """
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="invites"
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=50, choices=WorkspaceMemberRole.choices, default=WorkspaceMemberRole.MEMBER
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    invited_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="workspace_invites_created"
    )
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("ACCEPTED", "Accepted"),
            ("EXPIRED", "Expired"),
            ("REVOKED", "Revoked"),
        ],
        default="PENDING"
    )

    class Meta:
        db_table = "workspace_invites"
        unique_together = [("workspace", "email", "status")]

    def __str__(self) -> str:
        return f"Invite for {self.email} to {self.workspace.slug}"

    @property
    def is_valid(self) -> bool:
        return (
            self.status == "PENDING" and 
            self.expires_at > timezone.now()
        )

    @classmethod
    def generate_token(cls) -> str:
        return secrets.token_urlsafe(32)
