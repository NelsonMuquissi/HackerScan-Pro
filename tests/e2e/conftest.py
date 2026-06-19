import os
import subprocess
import time
import pytest
import requests

BASE_URL = os.getenv('HACKERSCAN_BASE_URL', 'http://localhost:8000')

@pytest.fixture(scope='session')
def api_server():
    # Start server via docker-compose if not already running
    # Assume docker-compose.yml defines service "api"
    subprocess.Popen(['docker', 'compose', 'up', '-d', 'api'], cwd=os.path.abspath('.'))
    # Wait for health endpoint
    for _ in range(30):
        try:
            r = requests.get(f"{BASE_URL}/health/")
            if r.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        raise RuntimeError('API server did not become healthy')
    yield
    # Teardown
    subprocess.run(['docker', 'compose', 'down'], cwd=os.path.abspath('.'))

@pytest.fixture
def api_client(api_server):
    session = requests.Session()
    # Authenticate - assume endpoint /api/auth/login returns token
    resp = session.post(f"{BASE_URL}/api/auth/login/", json={"email": os.getenv('TEST_USER_EMAIL'), "password": os.getenv('TEST_USER_PASSWORD')})
    resp.raise_for_status()
    token = resp.json().get('token')
    session.headers.update({'Authorization': f'Token {token}'})
    return session
