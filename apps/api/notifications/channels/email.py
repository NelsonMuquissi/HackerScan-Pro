"""
Email notification channel.
Uses Django's built-in email backend (configurable via settings).

Config keys (from NotificationPreference.config):
    to        (str)  — recipient address; falls back to triggered_by email
    cc        (list) — optional CC list
    reply_to  (str)  — optional reply-to address
"""
import logging
from textwrap import dedent

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .base import BaseNotificationChannel, NotificationPayload

logger = logging.getLogger(__name__)


def _build_subject(payload: NotificationPayload) -> str:
    status_emoji = "✅" if payload.scan_status == "completed" else "❌"
    return (
        f"{status_emoji} [{payload.severity_label}] Scan finished — "
        f"{payload.target_host} · {payload.total_findings} finding(s)"
    )


def _build_text_body(payload: NotificationPayload) -> str:
    duration = (
        f"{payload.duration_seconds:.1f}s"
        if payload.duration_seconds is not None
        else "—"
    )
    return dedent(f"""
        HackScan Pro — Scan Completed
        ==============================

        Target  : {payload.target_host}
        Status  : {payload.scan_status.upper()}
        Duration: {duration}

        Findings Summary
        ────────────────
        Critical : {payload.critical_count}
        High     : {payload.high_count}
        Medium   : {payload.medium_count}
        Low      : {payload.low_count}
        Info     : {payload.info_count}
        ─────────────────
        Total    : {payload.total_findings}

        {f"View results: {payload.scan_url}" if payload.scan_url else ""}

        —
        HackScan Pro  |  Automated Security Scanning
        To unsubscribe, update your notification preferences in the dashboard.
    """).strip()


class EmailChannel(BaseNotificationChannel):
    name = "email"

    def send(self, payload: NotificationPayload, config: dict) -> None:
        recipient = config.get("to") or payload.triggered_by
        if not recipient:
            logger.warning("EmailChannel: no recipient for scan %s — skipping", payload.scan_id)
            return

        cc       = config.get("cc", [])
        reply_to = config.get("reply_to", "")

        subject  = _build_subject(payload)
        body_txt = _build_text_body(payload)

        # Attempt HTML render — falls back to plain text if template missing
        try:
            body_html = render_to_string(
                "notifications/scan_completed.html",
                {"payload": payload},
            )
        except Exception:
            body_html = None

        msg = EmailMultiAlternatives(
            subject=subject,
            body=body_txt,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
            cc=cc,
            reply_to=[reply_to] if reply_to else [],
        )
        if body_html:
            msg.attach_alternative(body_html, "text/html")

        try:
            msg.send(fail_silently=False)
            logger.info(
                "EmailChannel: sent scan %s notification to %s",
                payload.scan_id, recipient,
            )
        except Exception as exc:
            logger.error(
                "EmailChannel: failed to send scan %s notification to %s — %s",
                payload.scan_id, recipient, exc,
            )
            raise  # Let the Celery task handle retry logic
