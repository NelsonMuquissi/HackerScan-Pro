from functools import wraps
from django.http import JsonResponse
from core.exceptions import AuthenticationError
from .auth_flow import AuthServiceFlow
from django.contrib.auth import get_user_model

User = get_user_model()

def jwt_required(view_func):
    """
    Decorator for pure Django views that require JWT authentication.
    Expected Header: Authorization: Bearer <token>
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JsonResponse({
                "error": True,
                "code": "authentication_failed",
                "message": "Authentication credentials were not provided.",
                "detail": "Missing Authorization header"
            }, status=401)

        token = auth_header.split(" ")[1]
        try:
            payload = AuthServiceFlow.verify_token(token, token_type="access")
            user_id = payload.get("user_id")
            if not user_id:
                raise ValueError("Invalid token payload: missing user_id")
            
            # Attach user to request
            try:
                request.user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse({
                    "error": True,
                    "code": "authentication_failed",
                    "message": "User not found.",
                    "detail": f"User with ID {user_id} does not exist"
                }, status=401)

            return view_func(request, *args, **kwargs)
        except ValueError as e:
            return JsonResponse({
                "error": True,
                "code": "authentication_failed",
                "message": str(e),
                "detail": str(e)
            }, status=401)
        except Exception as e:
            return JsonResponse({
                "error": True,
                "code": "error",
                "message": "An unexpected error occurred during authentication.",
                "detail": str(e)
            }, status=500)

    return _wrapped_view
