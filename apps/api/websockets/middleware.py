import urllib.parse
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from users.auth_flow import AuthServiceFlow
from users.models import User

@database_sync_to_async
def get_user_from_jwt(token_string):
    """
    Validates the JWT token using internal AuthServiceFlow.
    Returns the User object if valid, else returns AnonymousUser.
    """
    try:
        # Verify the access token
        payload = AuthServiceFlow.verify_token(token_string, token_type="access")
        user_id = payload.get("user_id")
        
        if not user_id:
            return AnonymousUser()
            
        # Optional: verify if user is active
        user = User.objects.get(pk=user_id)
        if not user.is_active:
            return AnonymousUser()
            
        return user
    except (User.DoesNotExist, ValueError, Exception):
        return AnonymousUser()

class JWTAuthMiddleware(BaseMiddleware):
    """
    Middleware that reads a JWT token from the query string (?token=...)
    and populates scope["user"].
    """
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = urllib.parse.parse_qs(query_string)
        
        token = query_params.get("token", [None])[0]
        
        if token:
            scope["user"] = await get_user_from_jwt(token)
        else:
            scope["user"] = AnonymousUser()
            
        return await super().__call__(scope, receive, send)

def JWTAuthMiddlewareStack(inner):
    """
    Equivalent to AuthMiddlewareStack but using JWT.
    """
    return JWTAuthMiddleware(inner)
