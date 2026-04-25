import hashlib
from functools import wraps
from django.http import JsonResponse
from django.utils import timezone
from .auth_flow import AuthServiceFlow
from django.contrib.auth import get_user_model
from .models import APIKey

User = get_user_model()

def jwt_required(view_func):
    """
    Decorator for pure Django views that require authentication.
    Supports:
    1. JWT: Authorization: Bearer <token>
    2. API Key: X-API-Key: hs_live_...
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 1. Try API Key first
        api_key_str = request.headers.get("X-API-Key")
        if api_key_str:
            key_hash = hashlib.sha256(api_key_str.encode()).hexdigest()
            try:
                key = APIKey.objects.select_related("user").get(
                    key_hash=key_hash, 
                    is_active=True
                )
                if not key.expires_at or key.expires_at > timezone.now():
                    request.user = key.user
                    request.api_key = key
                    # Update last used
                    key.last_used_at = timezone.now()
                    key.save(update_fields=["last_used_at"])
                    return view_func(request, *args, **kwargs)
            except APIKey.DoesNotExist:
                pass # Fallback to JWT or fail

        # 2. Try JWT
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = AuthServiceFlow.verify_token(token, token_type="access")
                user_id = payload.get("user_id")
                if user_id:
                    try:
                        request.user = User.objects.get(id=user_id)
                        return view_func(request, *args, **kwargs)
                    except User.DoesNotExist:
                        return JsonResponse({
                            "error": True,
                            "code": "authentication_failed",
                            "message": "User not found."
                        }, status=401)
            except Exception as e:
                return JsonResponse({
                    "error": True,
                    "code": "authentication_failed",
                    "message": str(e)
                }, status=401)

        return JsonResponse({
            "error": True,
            "code": "authentication_failed",
            "message": "Authentication credentials were not provided."
        }, status=401)

    return _wrapped_view
