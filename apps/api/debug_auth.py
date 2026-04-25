import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

@pytest.mark.django_db
def test_debug_auth():
    from rest_framework.request import Request
    from rest_framework.views import APIView
    
    client = APIClient()
    url = reverse("billing-subscription")
    response = client.get(url)
    
    # Let's see what DRF thinks
    view = APIView()
    view.request = view.initialize_request(response.wsgi_request)
    
    with open("debug_results.txt", "w") as f:
        f.write(f"Status: {response.status_code} \n")
        f.write(f"Body: {response.json()} \n")
        f.write(f"Authenticators: {view.request.authenticators} \n")
        f.write(f"User: {view.request.user} \n")
        f.write(f"Is Auth: {view.request.user.is_authenticated}\n")
    
    pytest.fail("Check debug_results.txt")
