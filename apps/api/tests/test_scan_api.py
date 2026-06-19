import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def admin_user(db):
    user = User.objects.create_user(username='admin', email='admin@example.com', password='password123', is_staff=True)
    return user

@pytest.fixture
def auth_client(api_client, admin_user):
    token_response = api_client.post(reverse('api-token-auth'), {'username': admin_user.username, 'password': 'password123'})
    token = token_response.data.get('token')
    api_client.credentials(HTTP_AUTHORIZATION='Token ' + token)
    return api_client

SCAN_TYPES = [
    'port',
    'web',
    'subdomain',
    'vuln',
    'malware',
    'config',
]

@pytest.mark.parametrize('scan_type', SCAN_TYPES)
def test_start_scan(auth_client, scan_type):
    url = reverse('scan-start')  # assuming named URL
    payload = {'type': scan_type, 'target': 'example.com'}
    response = auth_client.post(url, payload, format='json')
    assert response.status_code == 202, f"Failed to start {scan_type} scan: {response.content}"
    assert 'scan_id' in response.data

def test_get_scan_status(auth_client, admin_user):
    # Start a scan first
    start_url = reverse('scan-start')
    resp = auth_client.post(start_url, {'type': 'web', 'target': 'example.com'}, format='json')
    scan_id = resp.data['scan_id']
    status_url = reverse('scan-detail', args=[scan_id])
    status_resp = auth_client.get(status_url)
    assert status_resp.status_code == 200
    assert status_resp.data['status'] in ['queued', 'running', 'completed', 'failed']
