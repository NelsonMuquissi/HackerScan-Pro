import json
from django.views import View
from django.http import JsonResponse
from core.exceptions import ServiceError, api_exception_response

class BaseView(View):
    """
    Base view for pure Django views in HackerScan Pro.
    Provides utility methods for JSON handling and consistent error responses.
    """
    _json_body = None

    @property
    def json_body(self):
        """Parse and cache the JSON request body."""
        if self._json_body is None:
            if not self.request.body:
                self._json_body = {}
            else:
                try:
                    self._json_body = json.loads(self.request.body)
                except json.JSONDecodeError:
                    self._json_body = {}
        return self._json_body

    def dispatch(self, request, *args, **kwargs):
        """
        Global exception handling for all HTTP methods in this view.
        Catches ServiceError and DRF ValidationError.
        """
        try:
            return super().dispatch(request, *args, **kwargs)
        except ServiceError as e:
            return api_exception_response(e)
        except Exception as e:
            # Handle DRF ValidationError if it's raised by serializers
            if e.__class__.__name__ == "ValidationError" and hasattr(e, "detail"):
                return JsonResponse({
                    "error": True,
                    "code": "validation_error",
                    "message": "Validation failed.",
                    "detail": e.detail
                }, status=400)
            
            # For unexpected errors, return 500
            return JsonResponse({
                "error": True,
                "code": "server_error",
                "message": "An unexpected server error occurred.",
                "detail": str(e)
            }, status=500)


    def success_response(self, data=None, status=200):
        """Return a successful JSON response."""
        response_data = data or {}
        return JsonResponse(response_data, status=status)

    def error_response(self, message, code="error", detail=None, status=400):
        """Return an error JSON response."""
        return JsonResponse({
            "error": True,
            "code": code,
            "message": message,
            "detail": detail or message
        }, status=status)
