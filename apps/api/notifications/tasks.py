"""
Celery tasks for the notifications app.

notify_scan_completed(scan_id)
  → routed to queue: notifications
  → retries up to 3 times with exponential back-off on transient failures
  → called automatically by scans.tasks.run_scan after every scan

Usage:
    from notifications.tasks import notify_scan_completed
    notify_scan_completed.delay(str(scan.id))
"""
import logging

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    name="notifications.notify_scan_completed",
    queue="notifications",
    max_retries=3,
    default_retry_delay=60,        # 1 min, then 2 min, then 4 min
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    acks_late=True,                # acknowledge only after success
)
def notify_scan_completed(self, scan_id: str) -> dict:
    """
    Deliver scan-completion notifications via all configured channels
    (email, webhook, …) for the workspace that owns the scan.

    Retries up to 3 times on failure with exponential back-off.
    Returns a summary dict for the Celery result backend.
    """
    from scans.models import Scan, ScanStatus              # noqa: PLC0415
    from notifications.services import NotificationService # noqa: PLC0415

    try:
        scan = Scan.objects.select_related(
            "target", "target__workspace", "triggered_by"
        ).get(pk=scan_id)
    except Scan.DoesNotExist:
        logger.error("notify_scan_completed: Scan %s not found — aborting", scan_id)
        return {"error": "Scan not found", "scan_id": scan_id}

    if scan.status not in (ScanStatus.COMPLETED, ScanStatus.FAILED):
        logger.info(
            "notify_scan_completed: Scan %s in status %s — skipping notification",
            scan_id, scan.status,
        )
        return {"skipped": True, "status": scan.status}

    logger.info(
        "notify_scan_completed: dispatching for scan %s (status=%s, findings=%d)",
        scan_id, scan.status, scan.total_findings,
    )

    NotificationService.notify_scan_completed(scan)

    return {
        "scan_id": scan_id,
        "status":  scan.status,
        "notified": True,
    }
