import logging
import requests
import json
from .base import BaseNotificationChannel, NotificationPayload

logger = logging.getLogger(__name__)

class SlackChannel(BaseNotificationChannel):
    """
    Delivers rich Slack notifications using Blocks API.
    """
    name = "slack"

    def send(self, payload: NotificationPayload, config: dict) -> None:
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            logger.error("SlackChannel: missing webhook_url in config")
            return

        severity_emoji = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🔵",
            "INFO": "⚪"
        }.get(payload.severity_label, "⚪")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji} Security Scan Completed: {payload.target_host}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Total Findings:* {payload.total_findings}"},
                    {"type": "mrkdwn", "text": f"*Max Severity:* {payload.severity_label}"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"• *Critical:* {payload.critical_count}\n"
                        f"• *High:* {payload.high_count}\n"
                        f"• *Medium:* {payload.medium_count}\n"
                        f"• *Low:* {payload.low_count}"
                    )
                }
            }
        ]

        if payload.scan_url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Full Report"},
                        "url": payload.scan_url,
                        "style": "primary"
                    }
                ]
            })

        slack_payload = {"blocks": blocks}

        try:
            response = requests.post(
                webhook_url,
                json=slack_payload,
                timeout=10
            )
            response.raise_for_status()
            logger.info("SlackChannel: delivered rich notification for scan %s", payload.scan_id)
        except Exception as e:
            logger.error("SlackChannel: failed to deliver Slack notification — %s", e)
