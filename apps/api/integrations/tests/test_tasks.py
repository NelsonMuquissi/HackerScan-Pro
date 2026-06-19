import pytest
from unittest.mock import patch, MagicMock
from integrations.tasks import send_webhook_task
from integrations.models import Webhook
from users.models import Workspace

@pytest.mark.django_db
@patch('integrations.tasks.requests.post')
def test_send_webhook_task_jira_auth(mock_post, db, user):
    workspace = Workspace.objects.create(name="Test", owner=user)
    webhook = Webhook.objects.create(
        workspace=workspace,
        name="Jira Integration",
        url="https://jira.example.com",
        type=Webhook.Type.JIRA,
        config={"email": "test@example.com", "api_token": "secret123", "project_key": "SEC"}
    )
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    payload = {"scan_id": "123", "target_host": "test.com", "scan_status": "completed"}
    
    send_webhook_task(str(webhook.id), "scan.completed", payload)
    
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    headers = kwargs.get('headers', {})
    
    # Check if Auth header is Basic Auth (base64 of test@example.com:secret123)
    # dGVzdEBleGFtcGxlLmNvbTpzZWNyZXQxMjM=
    assert "Authorization" in headers
    assert headers["Authorization"] == "Basic dGVzdEBleGFtcGxlLmNvbTpzZWNyZXQxMjM="

@pytest.mark.django_db
@patch('integrations.tasks.requests.post')
def test_send_webhook_task_splunk_auth(mock_post, db, user):
    workspace = Workspace.objects.create(name="Test", owner=user)
    webhook = Webhook.objects.create(
        workspace=workspace,
        name="Splunk Integration",
        url="https://splunk.example.com",
        type=Webhook.Type.SPLUNK,
        config={"hec_token": "my-hec-token"}
    )
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    payload = {"scan_id": "123", "target_host": "test.com", "scan_status": "completed"}
    
    send_webhook_task(str(webhook.id), "scan.completed", payload)
    
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    headers = kwargs.get('headers', {})
    
    assert "Authorization" in headers
    assert headers["Authorization"] == "Splunk my-hec-token"
