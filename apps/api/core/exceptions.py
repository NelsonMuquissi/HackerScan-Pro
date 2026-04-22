"""
Custom exception handlers for HackScan Pro API.
Always returns a consistent JSON structure: { error, detail, code }.
"""
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import APIException
from rest_framework import status


from django.http import JsonResponse

def api_exception_response(exc):
    """
    Generate a JsonResponse for a ServiceError or subclass.
    Matches the structure of custom_exception_handler for consistency.
    """
    status_code = getattr(exc, "status_code", 400)
    code = getattr(exc, "default_code", "error")
    detail = getattr(exc, "detail", str(exc))
    message = str(detail)

    return JsonResponse({
        "error": True,
        "code": str(code),
        "message": message,
        "detail": detail,
    }, status=status_code)


def custom_exception_handler(exc, context):

    """
    Override DRF's default exception handler to always return a
    unified shape: { "error": bool, "code": str, "detail": str|list }.
    """
    response = drf_exception_handler(exc, context)

    if response is not None:
        original_data = response.data
        code = getattr(exc, "default_code", "error")

        # Flatten list / dict detail
        if isinstance(original_data, list):
            detail = original_data
            message = " ".join([str(x) for x in detail])
        elif isinstance(original_data, dict):
            if "detail" in original_data:
                detail = original_data["detail"]
                if hasattr(detail, "code"):
                    code = detail.code
                message = str(detail)
                detail = str(detail)
            else:
                detail = original_data
                msgs = []
                for k, v in detail.items():
                    if isinstance(v, list) and v:
                        msgs.append(f"{k}: {v[0]}")
                    else:
                        msgs.append(f"{k}: {v}")
                message = " | ".join(msgs) if msgs else "Validation error"
        else:
            detail = str(original_data)
            message = detail

        response.data = {
            "error": True,
            "code": str(code),
            "message": message,
            "detail": detail,
        }

    return response


class ServiceError(APIException):
    """Base class for business-logic errors raised by services."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "service_error"
    default_detail = "An error occurred processing the request."


class NotFoundError(ServiceError):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "not_found"
    default_detail = "Resource not found."


class ConflictError(ServiceError):
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"
    default_detail = "Resource already exists."


class ForbiddenError(ServiceError):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "forbidden"
    default_detail = "You do not have permission to perform this action."


class AuthenticationError(ServiceError):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "authentication_failed"
    default_detail = "Authentication credentials are invalid or expired."


class TwoFactorRequiredError(ServiceError):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "2fa_required"
    default_detail = "Two-factor authentication is required."
