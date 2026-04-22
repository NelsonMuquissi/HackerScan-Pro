"""
Webhook notification channel.
Sends an HMAC-signed HTTP POST to a user-configured URL.

Config keys (from NotificationPreference.config):
    url        (str)  — REQUIRED. The endpoint to POST to.
    secret     (str)  — Optional HMAC-SHA256 secret for signature header.
    timeout    (int)  — HTTP timeout in seconds (default: 10).
    headers    (dict) — Extra HTTP headers to include.

The payload is the standard HackScan notification envelope (JSON).
The HMAC signature is sent as: X-HackScan-Signature: sha256=<hex>
"""
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone

from .base import BaseNotificationChannel, NotificationPayload

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10


def _build_body(payload: NotificationPayload) -> dict:
    return {
        "event":     "scan.completed",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "scan": {
            "id":              payload.scan_id,
            "status":          payload.scan_status,
            "target_host":     payload.target_host,
            "workspace_id":    payload.workspace_id,
            "duration_seconds": payload.duration_seconds,
            "scan_url":        payload.scan_url,
            "triggered_by":    payload.triggered_by,
        },
        "findings": {
            "total":    payload.total_findings,
            "critical": payload.critical_count,
            "high":     payload.high_count,
            "medium":   payload.medium_count,
            "low":      payload.low_count,
            "info":     payload.info_count,
        },
    }


def _sign(body_bytes: bytes, secret: str) -> str:
    """Returns sha256=<hex> HMAC signature."""
    mac = hmac.new(
        key=secret.encode(),
        msg=body_bytes,
        digestmod=hashlib.sha256,
    )
    return f"sha256={mac.hexdigest()}"


class WebhookChannel(BaseNotificationChannel):
    name = "webhook"

    def send(self, payload: NotificationPayload, config: dict) -> None:
        url = config.get("url", "").strip()
        if not url:
            logger.warning("WebhookChannel: no URL configured for scan %s — skipping", payload.scan_id)
            return

        secret      = config.get("secret", "")
        timeout     = int(config.get("timeout", DEFAULT_TIMEOUT))
        extra_hdrs  = config.get("headers", {})

        body_dict  = _build_body(payload)
        body_bytes = json.dumps(body_dict, default=str).encode("utf-8")

        headers = {
            "Content-Type":          "application/json",
            "User-Agent":            "HackScanPro-Webhook/1.0",
            "X-HackScan-Event":      "scan.completed",
            "X-HackScan-Scan-Id":    payload.scan_id,
        }
        if secret:
            headers["X-HackScan-Signature"] = _sign(body_bytes, secret)
        headers.update(extra_hdrs)  # allow per-integration overrides

        req = urllib.request.Request(url, data=body_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
            if 200 <= status < 300:
                logger.info(
                    "WebhookChannel: scan %s → %s responded %d",
                    payload.scan_id, url, status,
                )
            else:
                logger.warning(
                    "WebhookChannel: scan %s → %s responded non-2xx %d",
                    payload.scan_id, url, status,
                )
        except urllib.error.HTTPError as exc:
            logger.error(
                "WebhookChannel: scan %s → %s HTTP %d — %s",
                payload.scan_id, url, exc.code, exc,
            )
            raise
        except Exception as exc:
            logger.error(
                "WebhookChannel: scan %s → %s failed — %s",
                payload.scan_id, url, exc,
            )
            raise
