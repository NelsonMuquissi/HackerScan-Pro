"""
HackScan Pro — Stripe Webhook Endpoint.

This view:
  - Accepts raw POST bodies from Stripe (no DRF auth required)
  - Verifies the Stripe-Signature header
  - Delegates to BillingService.handle_webhook
"""
import logging

from django.http import HttpResponse
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)

from .services import BillingService

logger = logging.getLogger(__name__)


@api_view(["POST"])
@authentication_classes([])   # Stripe doesn't send a Bearer token
@permission_classes([])       # AllowAny — signature is verified inside handle_webhook
def stripe_webhook_view(request):
    """
    POST /v1/billing/webhooks/stripe/

    Stripe sends webhook events here. The raw body + Stripe-Signature
    header are forwarded to BillingService for verification and dispatch.
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        BillingService.handle_webhook(payload, sig_header)
    except ValueError as exc:
        logger.warning("Stripe webhook rejected: %s", exc)
        return HttpResponse(status=400)

    return HttpResponse(status=200)
