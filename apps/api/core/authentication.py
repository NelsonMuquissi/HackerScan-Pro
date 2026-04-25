"""
HackScan Pro — Authentication Backends.
Supports JWT (via custom decorator) and API Keys (DRF-style backend).
"""
import hashlib
from rest_framework import authentication
from rest_framework import exceptions
from django.utils import timezone
from users.models import APIKey

class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    Authentication backend that validates hs_live_... keys.
    Expected Header: X-API-Key: hs_live_...
    """

    def authenticate(self, request):
        api_key_str = request.headers.get("X-API-Key")
        if not api_key_str:
            return None

        # Hash the key to find it in the database
        key_hash = hashlib.sha256(api_key_str.encode()).hexdigest()

        try:
            key = APIKey.objects.select_related("user", "workspace").get(
                key_hash=key_hash, 
                is_active=True
            )
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid API Key.")

        # Check expiration
        if key.expires_at and key.expires_at < timezone.now():
            raise exceptions.AuthenticationFailed("API Key has expired.")

        # Update last used
        key.last_used_at = timezone.now()
        key.save(update_fields=["last_used_at"])

        # Attach workspace to request for easier access in scoped views
        request.workspace = key.workspace
        
        return (key.user, key)
