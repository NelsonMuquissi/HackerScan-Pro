import pytest
import structlog
from django.urls import reverse
from rest_framework.test import APIClient
import json
from users.services import UserService

# Force structlog to be quiet
structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
    logger_factory=structlog.get_logger
)

@pytest.mark.django_db
def test_register_debug(client):
    url = reverse("auth-register")
    payload = {
        "email": "test-new@example.com",
        "password": "Password123!",
        "full_name": "Test User"
    }
    
    response = client.post(url, payload, content_type="application/json")
    print(f"\nRegister Status: {response.status_code}")
    print(f"Register Body: {response.content.decode()}")

@pytest.mark.django_db
def test_duplicate_register_debug(client):
    url = reverse("auth-register")
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
        "full_name": "Test User"
    }
    
    # First registration
    UserService.register(email=payload["email"], password=payload["password"], full_name=payload["full_name"])
    
    # Second registration
    response = client.post(url, payload, content_type="application/json")
    print(f"\nDuplicate Register Status: {response.status_code}")
    print(f"Duplicate Register Body: {response.content.decode()}")

@pytest.mark.django_db
def test_login_debug(client):
    email = "test-login@example.com"
    password = "Password123!"
    
    # Register user first using the service to ensure correct hashing
    from users.models import User
    User.objects.filter(email=email).delete()
    
    user = UserService.register(
        email=email,
        password=password,
        full_name="Test Login"
    )
    # Ensure email is verified in DB for login
    User.objects.filter(id=user.id).update(email_verified=True)

    url = reverse("auth-login")
    payload = {
        "email": email,
        "password": password
    }
    response = client.post(url, payload, content_type="application/json")
    print(f"\nLogin Status: {response.status_code}")
    print(f"Login Body: {response.content.decode()}")
