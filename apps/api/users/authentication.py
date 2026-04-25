from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils.translation import gettext_lazy as _
from .auth_flow import AuthServiceFlow
from .models import User, APIKey

class CustomJWTAuthentication(BaseAuthentication):
    """
    Custom DRF Authentication class that uses PyJWT powered AuthServiceFlow.
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]
        try:
            payload = AuthServiceFlow.verify_token(token, token_type="access")
            user_id = payload.get("user_id")
            if not user_id:
                raise AuthenticationFailed(_("Invalid token payload"), code="authentication_failed")

            user = User.objects.get(pk=user_id)
            if not user.is_active:
                raise AuthenticationFailed(_("User is inactive"), code="user_inactive")

            return (user, token)
        except User.DoesNotExist:
            raise AuthenticationFailed(_("User not found"), code="user_not_found")
        except ValueError as e:
            raise AuthenticationFailed(str(e), code="authentication_failed")

    def authenticate_header(self, request):
        return 'Bearer'


class APIKeyAuthentication(BaseAuthentication):
    """
    Custom DRF Authentication for X-API-Key based access.
    Automatically scopes the request to the key's workspace.
    """
    def authenticate(self, request):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return None

        key_obj = APIKey.authenticate(api_key)
        if not key_obj:
            raise AuthenticationFailed(_("Invalid or expired API Key"), code="invalid_api_key")

        # Inject workspace into the request object for global access in views/services
        request.workspace = key_obj.workspace
        
        # Track usage
        from django.utils import timezone
        APIKey.objects.filter(pk=key_obj.pk).update(last_used_at=timezone.now())

        return (key_obj.user, key_obj)

    def authenticate_header(self, request):
        return 'Api-Key'
