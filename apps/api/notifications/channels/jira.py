import logging
import requests
import json
from .base import BaseNotificationChannel, NotificationPayload

logger = logging.getLogger(__name__)

class JiraChannel(BaseNotificationChannel):
    """
    Creates Jira issues for high-severity findings discovered during a scan.
    """
    name = "jira"

    def send(self, payload: NotificationPayload, config: dict) -> None:
        jira_url = config.get("url")
        email = config.get("email")
        api_token = config.get("api_token")
        project_key = config.get("project_key")
        issue_type = config.get("issue_type", "Bug")

        if not all([jira_url, email, api_token, project_key]):
            logger.error("JiraChannel: missing required config (url, email, api_token, project_key)")
            return

        # We only create a Jira issue for the scan summary, 
        # or we could iterate through findings if the payload had them.
        # For now, we create a summary issue for the scan.
        
        summary = f"Security Scan Completed: {payload.target_host} - {payload.severity_label} Findings"
        description = (
            f"HackerScan Pro detected {payload.total_findings} findings on {payload.target_host}.\n\n"
            f"* Critical: {payload.critical_count}\n"
            f"* High: {payload.high_count}\n"
            f"* Medium: {payload.medium_count}\n"
            f"* Low: {payload.low_count}\n\n"
            f"View details: {payload.scan_url or 'https://dashboard.hackerscan.pro'}"
        )

        jira_payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
                "priority": {"name": self._map_severity_to_priority(payload.severity_label)}
            }
        }

        # Handle Jira Server vs Cloud (Cloud uses /rest/api/3/issue)
        endpoint = f"{jira_url.rstrip('/')}/rest/api/2/issue"
        
        try:
            response = requests.post(
                endpoint,
                auth=(email, api_token),
                json=jira_payload,
                timeout=10
            )
            response.raise_for_status()
            logger.info("JiraChannel: created Jira issue for scan %s", payload.scan_id)
        except Exception as e:
            logger.error("JiraChannel: failed to create Jira issue — %s", e)

    def _map_severity_to_priority(self, severity: str) -> str:
        mapping = {
            "CRITICAL": "Highest",
            "HIGH": "High",
            "MEDIUM": "Medium",
            "LOW": "Low",
            "INFO": "Lowest"
        }
        return mapping.get(severity, "Medium")
