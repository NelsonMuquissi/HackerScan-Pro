import json

class BaseFormatter:
    @staticmethod
    def format(payload: dict, event_type: str, config: dict) -> dict:
        """
        Default formatter that returns the payload as-is.
        """
        return payload


class SlackFormatter(BaseFormatter):
    @staticmethod
    def format(payload: dict, event_type: str, config: dict) -> dict:
        """
        Transforms HackerScan payload into Slack Block Kit format.
        """
        scan_id = payload.get("scan_id", "Unknown")
        target = payload.get("target_host", "Unknown Target")
        status = payload.get("scan_status", "Unknown Status").upper()
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"HackerScan Alert: Scan {status}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Target:*\n{target}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Scan ID:*\n{scan_id}"
                    }
                ]
            }
        ]
        
        # Add finding counts if available
        if "critical_count" in payload:
            critical = payload.get("critical_count", 0)
            high = payload.get("high_count", 0)
            medium = payload.get("medium_count", 0)
            low = payload.get("low_count", 0)
            
            blocks.append({
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Critical:* {critical} \U0001F6A8"},
                    {"type": "mrkdwn", "text": f"*High:* {high} \U0001F534"},
                    {"type": "mrkdwn", "text": f"*Medium:* {medium} \U0001F7E0"},
                    {"type": "mrkdwn", "text": f"*Low:* {low} \U0001F7E1"}
                ]
            })

        return {"blocks": blocks}


class JiraFormatter(BaseFormatter):
    @staticmethod
    def format(payload: dict, event_type: str, config: dict) -> dict:
        """
        Transforms HackerScan payload into Jira Issue format.
        Requires 'project_key' in config.
        """
        project_key = config.get("project_key", "SEC")
        target = payload.get("target_host", "Unknown Target")
        status = payload.get("scan_status", "Unknown Status")
        
        description = "HackerScan completed a scan.\n\n"
        for k, v in payload.items():
            description += f"*{k}*: {v}\n"
            
        issue = {
            "fields": {
                "project": {
                    "key": project_key
                },
                "summary": f"[HackerScan] Scan {status} on {target}",
                "description": description,
                "issuetype": {
                    "name": "Task"
                }
            }
        }
        return issue


class SplunkFormatter(BaseFormatter):
    @staticmethod
    def format(payload: dict, event_type: str, config: dict) -> dict:
        """
        Transforms HackerScan payload into Splunk HEC event format.
        """
        source = config.get("source", "hackerscan")
        sourcetype = config.get("sourcetype", "_json")
        
        return {
            "source": source,
            "sourcetype": sourcetype,
            "event": payload
        }


class FormatterFactory:
    @staticmethod
    def get_formatter(webhook_type: str):
        formatters = {
            'SLACK': SlackFormatter,
            'JIRA': JiraFormatter,
            'SPLUNK': SplunkFormatter,
            'GENERIC': BaseFormatter
        }
        return formatters.get(webhook_type, BaseFormatter)
