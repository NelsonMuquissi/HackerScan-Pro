"""
NotificationService — loads the active channels for a workspace
and dispatches a NotificationPayload to each one.

Usage (from a Celery task):
    NotificationService.notify_scan_completed(scan)
"""
import logging

from .channels.base import NotificationPayload
from .channels.email import EmailChannel
from .channels.webhook import WebhookChannel
from .models import NotificationPreference

logger = logging.getLogger(__name__)

# Registry maps channel type slug → channel instance
_CHANNEL_REGISTRY = {
    "email":   EmailChannel(),
    "webhook": WebhookChannel(),
}


class NotificationService:
    @staticmethod
    def send(user, channel: str, template: str, context: dict) -> None:
        """
        Generic method to send a direct notification to a user bypassing scan preferences.
        """
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.conf import settings
        from .models import Notification

        try:
            # Create in-app notification
            Notification.objects.create(
                user=user,
                type=Notification.Type.BILLING_ALERT if "billing" in template else Notification.Type.SYSTEM_UPDATE,
                title=f"Notification: {template}",
                message=str(context)
            )
        except Exception as e:
            logger.error(f"NotificationService: failed to create in-app notification: {e}")

        if channel == "email":
            try:
                subject = "HackScan Pro Alert"
                body_txt = f"Review your dashboard for context: {context}"
                try:
                    body_html = render_to_string(f"{template}.html", context)
                except Exception:
                    body_html = None
                
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=body_txt,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email],
                )
                if body_html:
                    msg.attach_alternative(body_html, "text/html")
                msg.send(fail_silently=False)
                logger.info("NotificationService: sent generic notification to %s", user.email)
            except Exception as e:
                logger.error("NotificationService: failed to send generic notification to %s - %s", user.email, e)

    @staticmethod
    def notify_scan_completed(scan) -> None:
        """
        Build a NotificationPayload from a completed Scan and deliver it
        to every active channel configured for the scan's workspace.
        Also creates an in-app Notification record for the UI.
        """
        from .models import Notification  # noqa: PLC0415
        workspace = scan.target.workspace
        user = scan.triggered_by

        # 1. Create in-app notification (mandatory for UI visibility)
        if user:
            try:
                Notification.objects.create(
                    user=user,
                    type=Notification.Type.SCAN_COMPLETED,
                    title=f"Scan Completed: {scan.target.host}",
                    message=f"The {scan.scan_type} scan finished with {scan.total_findings} findings.",
                    data={
                        "scan_id": str(scan.id),
                        "status": scan.status,
                        "critical_count": scan.critical_count,
                        "high_count": scan.high_count,
                    }
                )
            except Exception as e:
                logger.error(f"NotificationService: failed to create in-app notification: {e}")

        # 2. Dispatch to external channels (email, webhooks)
        payload = NotificationPayload(
            scan_id=str(scan.id),
            scan_status=scan.status,
            target_host=scan.target.host,
            workspace_id=str(workspace.id),
            triggered_by=user.email if user else "",
            total_findings=scan.total_findings,
            critical_count=scan.critical_count,
            high_count=scan.high_count,
            medium_count=scan.medium_count,
            low_count=scan.low_count,
            info_count=scan.info_count,
            duration_seconds=scan.duration_seconds,
        )

        preferences = NotificationPreference.objects.filter(
            workspace=workspace,
            is_active=True,
            **_event_filter(scan.status),
        )

        if not preferences.exists():
            logger.info(
                "NotificationService: no active preferences for workspace %s — scan %s",
                workspace.id, scan.id,
            )
            return

        for pref in preferences:
            channel = _CHANNEL_REGISTRY.get(pref.channel)
            if channel is None:
                logger.warning(
                    "NotificationService: unknown channel type %r — preference %s",
                    pref.channel, pref.id,
                )
                continue
            try:
                channel.send(payload=payload, config=pref.config)
            except Exception as exc:
                # Individual channel failures are isolated — log and continue
                logger.error(
                    "NotificationService: channel %r failed for scan %s — %s",
                    pref.channel, scan.id, exc,
                )

        # 3. Dispatch to Enterprise Webhooks (Integrations App)
        try:
            from integrations.services import WebhookDispatcherService  # noqa: PLC0415
            WebhookDispatcherService.dispatch(
                workspace_id=workspace.id,
                event_type="scan.completed" if scan.status == "completed" else "scan.failed",
                payload=payload.__dict__
            )
        except Exception as e:
            logger.error("NotificationService: failed to dispatch enterprise webhooks: %s", e)


def _event_filter(status: str) -> dict:
    """Return the ORM filter kwargs for the scan status event."""
    if status == "completed":
        return {"notify_on_complete": True}
    if status == "failed":
        return {"notify_on_failed": True}
    return {}
