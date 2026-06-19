import logging
import requests
import json
from .base import BaseNotificationChannel, NotificationPayload

logger = logging.getLogger(__name__)

class SplunkChannel(BaseNotificationChannel):
    """
    Delivers scan findings to Splunk via the HTTP Event Collector (HEC).
    """
    name = "splunk"

    def send(self, payload: NotificationPayload, config: dict) -> None:
        hec_url = config.get("hec_url")
        hec_token = config.get("hec_token")
        index = config.get("index", "main")
        sourcetype = config.get("sourcetype", "hackerscan:scan")

        if not hec_url or not hec_token:
            logger.error("SplunkChannel: missing hec_url or hec_token in config")
            return

        # Splunk HEC expects a specific wrapper
        splunk_event = {
            "time": payload.duration_seconds or 0, # Or current time if preferred
            "host": payload.target_host,
            "source": "hackerscan-pro",
            "sourcetype": sourcetype,
            "index": index,
            "event": payload.__dict__
        }

        headers = {
            "Authorization": f"Splunk {hec_token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(
                hec_url,
                data=json.dumps(splunk_event),
                headers=headers,
                timeout=10,
                verify=config.get("verify_ssl", True)
            )
            response.raise_for_status()
            logger.info("SplunkChannel: delivered scan %s to Splunk HEC", payload.scan_id)
        except Exception as e:
            logger.error("SplunkChannel: failed to deliver to Splunk — %s", e)
