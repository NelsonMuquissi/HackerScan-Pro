import hashlib
import hmac
import json
import pytest
from unittest.mock import patch, MagicMock
from django.core import mail
from notifications.channels.base import NotificationPayload
from notifications.channels.splunk import SplunkChannel
from notifications.channels.jira import JiraChannel
from notifications.channels.slack import SlackChannel
from notifications.channels.email import EmailChannel
from notifications.channels.webhook import WebhookChannel

@pytest.fixture
def payload():
    return NotificationPayload(
        scan_id="test-scan-id",
        workspace_id="test-workspace-id",
        target_host="example.com",
        scan_status="completed",
        total_findings=10,
        critical_count=1,
        high_count=2,
        medium_count=3,
        low_count=4,
        info_count=0,
        duration_seconds=120.5,
        scan_url="https://dashboard.hackerscan.pro/scans/test-scan-id",
        triggered_by="admin@example.com"
    )

class TestSplunkChannel:
    @patch("requests.post")
    def test_send_success(self, mock_post, payload):
        mock_post.return_value.raise_for_status.return_value = None
        
        channel = SplunkChannel()
        config = {
            "hec_url": "https://splunk.example.com/services/collector",
            "hec_token": "test-token",
            "index": "security",
            "sourcetype": "hackerscan:test"
        }
        
        channel.send(payload, config)
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == config["hec_url"]
        assert kwargs["headers"]["Authorization"] == f"Splunk {config['hec_token']}"
        
        data = kwargs["data"]
        import json
        event_data = json.loads(data)
        assert event_data["index"] == "security"
        assert event_data["event"]["scan_id"] == "test-scan-id"

    @patch("requests.post")
    def test_send_missing_config(self, mock_post, payload):
        channel = SplunkChannel()
        channel.send(payload, {})
        mock_post.assert_not_called()

class TestJiraChannel:
    @patch("requests.post")
    def test_send_success(self, mock_post, payload):
        mock_post.return_value.raise_for_status.return_value = None
        
        channel = JiraChannel()
        config = {
            "url": "https://jira.example.com",
            "email": "user@example.com",
            "api_token": "jira-token",
            "project_key": "SEC",
            "issue_type": "Security Vulnerability"
        }
        
        channel.send(payload, config)
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "jira.example.com/rest/api/2/issue" in args[0]
        assert kwargs["auth"] == ("user@example.com", "jira-token")
        
        jira_payload = kwargs["json"]
        assert jira_payload["fields"]["project"]["key"] == "SEC"
        assert "Security Scan Completed" in jira_payload["fields"]["summary"]
        assert jira_payload["fields"]["priority"]["name"] == "Highest"

class TestSlackChannel:
    @patch("requests.post")
    def test_send_success(self, mock_post, payload):
        mock_post.return_value.raise_for_status.return_value = None
        
        channel = SlackChannel()
        config = {
            "webhook_url": "https://hooks.slack.com/services/T000/B000/XXXX"
        }
        
        channel.send(payload, config)
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == config["webhook_url"]
        
        slack_payload = kwargs["json"]
        assert "blocks" in slack_payload
        assert any("Security Scan Completed" in str(block) for block in slack_payload["blocks"])
        assert any("Total Findings" in str(block) for block in slack_payload["blocks"])

class TestEmailChannel:
    def test_send_success(self, payload):
        channel = EmailChannel()
        config = {
            "to": "security-team@example.com",
            "cc": ["manager@example.com"]
        }
        
        channel.send(payload, config)
            
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == ["security-team@example.com"]
        assert email.cc == ["manager@example.com"]
        assert "Scan finished" in email.subject
        assert "Target  : example.com" in email.body

    def test_send_missing_recipient(self, payload):
        payload.triggered_by = ""
        channel = EmailChannel()
        channel.send(payload, {})
        assert len(mail.outbox) == 0

class TestWebhookChannel:
    @patch("urllib.request.urlopen")
    def test_send_success(self, mock_urlopen, payload):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        channel = WebhookChannel()
        config = {
            "url": "https://webhook.site/test",
            "secret": "super-secret"
        }
        
        channel.send(payload, config)
        
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.get_full_url() == config["url"]
        # urllib Request normalizes headers (capitalizes first letter, rest lowercase)
        assert req.get_header("Content-type") == "application/json"
        assert any(h.lower() == "x-hackscan-signature" for h in req.headers)
        
        body = json.loads(req.data.decode("utf-8"))
        assert body["scan"]["id"] == "test-scan-id"
        assert body["findings"]["total"] == 10

    @patch("urllib.request.urlopen")
    def test_send_failure(self, mock_urlopen, payload):
        mock_urlopen.side_effect = Exception("Network error")
        
        channel = WebhookChannel()
        with pytest.raises(Exception, match="Network error"):
            channel.send(payload, {"url": "https://fail.com"})
