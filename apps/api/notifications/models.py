"""
HackScan Pro — Notification Models.

Notification          → in-app notification record (per user)
NotificationPreference → per-workspace channel/event configuration
"""
from django.db import models
from django.conf import settings

from core.models import UUIDModel, TimestampedModel


class Notification(UUIDModel, TimestampedModel):
    class Type(models.TextChoices):
        SCAN_COMPLETED = "SCAN_COMPLETED", "Scan Completed"
        VULNERABILITY_FOUND = "VULNERABILITY_FOUND", "Vulnerability Found"
        BILLING_ALERT = "BILLING_ALERT", "Billing Alert"
        SYSTEM_UPDATE = "SYSTEM_UPDATE", "System Update"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=50, choices=Type.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.type} - {self.user.email}"


class NotificationPreference(UUIDModel, TimestampedModel):
    """
    Per-workspace notification channel configuration.
    Each record maps one channel (email / webhook) to one workspace,
    with toggles for which events trigger delivery.
    """
    workspace = models.ForeignKey(
        "users.Workspace",
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    channel = models.CharField(
        max_length=50,
        help_text='Channel slug: "email", "webhook"',
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text='Channel-specific config, e.g. {"to": "user@example.com"}',
    )
    is_active = models.BooleanField(default=True)
    notify_on_complete = models.BooleanField(default=True)
    notify_on_failed = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("workspace", "channel")]

    def __str__(self):
        return f"{self.channel} → {self.workspace} (active={self.is_active})"
