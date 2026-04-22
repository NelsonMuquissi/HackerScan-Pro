"""
Abstract base class for all notification channels.

Every channel receives a NotificationPayload and decides how to deliver it.
Channel implementations MUST be idempotent — they may be retried by Celery.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class NotificationPayload:
    """
    Structured data passed to every notification channel.
    Populated by NotificationService from a completed Scan.
    """
    scan_id:       str
    scan_status:   str          # completed | failed
    target_host:   str
    workspace_id:  str
    triggered_by:  str          # user email
    total_findings:     int = 0
    critical_count:     int = 0
    high_count:         int = 0
    medium_count:       int = 0
    low_count:          int = 0
    info_count:         int = 0
    duration_seconds:   float | None = None
    scan_url:           str = ""   # deep-link to dashboard (optional)
    extra:              dict = field(default_factory=dict)

    @property
    def severity_label(self) -> str:
        """Returns the highest severity found, for subject lines."""
        if self.critical_count:
            return "CRITICAL"
        if self.high_count:
            return "HIGH"
        if self.medium_count:
            return "MEDIUM"
        if self.low_count:
            return "LOW"
        return "INFO"


class BaseNotificationChannel(ABC):
    """
    Abstract notification channel interface.
    All channels must implement `send()`.
    """
    name: str = ""

    @abstractmethod
    def send(self, payload: NotificationPayload, config: dict) -> None:
        """
        Deliver the notification.

        Args:
            payload: Structured scan result data.
            config:  Channel-specific settings from NotificationPreference.config
                     (e.g. {"to": "user@example.com"} for email,
                           {"url": "https://hooks.example.com/…"} for webhook).

        Must NOT raise — catch all exceptions internally and log them.
        """
        ...
