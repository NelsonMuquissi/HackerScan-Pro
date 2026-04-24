"""
HackScan Pro — Billing API Views.

Endpoints:
  GET    /v1/billing/plans/          → list active plans
  GET    /v1/billing/subscription/   → current workspace subscription
  POST   /v1/billing/subscription/   → create Stripe checkout session
  PATCH  /v1/billing/subscription/   → change plan (via checkout)
  DELETE /v1/billing/subscription/   → cancel subscription
  GET    /v1/billing/invoices/       → list workspace invoices
  GET    /v1/billing/usage/          → current period usage
  POST   /v1/billing/portal/         → Stripe customer portal URL
"""
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import Workspace

from .models import Invoice, Plan, Subscription, UsageRecord
from .serializers import (
    CreateCheckoutSerializer,
    CreatePortalSerializer,
    InvoiceSerializer,
    PlanSerializer,
    SubscriptionSerializer,
    UsageRecordSerializer,
)
from .services import BillingService
from scans.views import WorkspaceScopedViewMixin
from core.permissions import IsWorkspaceAdmin


# ─── Helpers ─────────────────────────────────────────────────────────────────


# Local _get_workspace removed in favor of WorkspaceScopedViewMixin logic


# ─── Plans ───────────────────────────────────────────────────────────────────


class PlanListView(generics.ListAPIView):
    """GET /v1/billing/plans/ — returns all active plans."""
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]  # plans are public info

    def get_queryset(self):
        return Plan.objects.filter(is_active=True).order_by("price_monthly")


# ─── Subscription ────────────────────────────────────────────────────────────


class SubscriptionView(WorkspaceScopedViewMixin, APIView):
    """
    GET    → current subscription
    POST   → create Stripe checkout session
    PATCH  → change plan (new checkout)
    DELETE → cancel at period end
    """
    permission_classes = [IsWorkspaceAdmin]

    def get(self, request):
        wid = self.get_workspace_id(request)
        workspace = get_object_or_404(Workspace, id=wid)
        try:
            subscription = workspace.subscription
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "No active subscription."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)

    def post(self, request):
        serializer = CreateCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        wid = self.get_workspace_id(request)
        workspace = get_object_or_404(Workspace, id=wid)
        try:
            plan = Plan.objects.get(id=data["plan_id"], is_active=True)
        except Plan.DoesNotExist:
            return Response(
                {"detail": "Plan not found."}, status=status.HTTP_404_NOT_FOUND,
            )

        checkout_url = BillingService.create_checkout_session(
            workspace=workspace,
            plan=plan,
            billing_cycle=data["billing_cycle"],
            success_url=data["success_url"],
            cancel_url=data["cancel_url"],
        )
        return Response({"checkout_url": checkout_url}, status=status.HTTP_201_CREATED)

    def patch(self, request):
        """Change plan — creates a new checkout session for the new plan."""
        serializer = CreateCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        wid = self.get_workspace_id(request)
        workspace = get_object_or_404(Workspace, id=wid)
        try:
            plan = Plan.objects.get(id=data["plan_id"], is_active=True)
        except Plan.DoesNotExist:
            return Response(
                {"detail": "Plan not found."}, status=status.HTTP_404_NOT_FOUND,
            )

        checkout_url = BillingService.create_checkout_session(
            workspace=workspace,
            plan=plan,
            billing_cycle=data["billing_cycle"],
            success_url=data["success_url"],
            cancel_url=data["cancel_url"],
        )
        return Response({"checkout_url": checkout_url})

    def delete(self, request):
        """Cancel subscription at end of current billing period."""
        wid = self.get_workspace_id(request)
        workspace = get_object_or_404(Workspace, id=wid)
        try:
            subscription = workspace.subscription
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "No active subscription."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if subscription.stripe_subscription_id:
            import stripe  # noqa: PLC0415
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True,
            )

        subscription.cancel_at_period_end = True
        subscription.save(update_fields=["cancel_at_period_end", "updated_at"])

        return Response({"detail": "Subscription will cancel at end of period."})


# ─── Invoices ────────────────────────────────────────────────────────────────


class InvoiceListView(WorkspaceScopedViewMixin, generics.ListAPIView):
    """GET /v1/billing/invoices/ — paginated list of workspace invoices."""
    serializer_class = InvoiceSerializer
    permission_classes = [IsWorkspaceAdmin]

    def get_queryset(self):
        wid = self.get_workspace_id(self.request)
        return Invoice.objects.filter(workspace_id=wid).order_by("-created_at")


# ─── Usage ───────────────────────────────────────────────────────────────────


class UsageView(WorkspaceScopedViewMixin, APIView):
    """GET /v1/billing/usage/ — current billing period usage."""
    permission_classes = [IsWorkspaceAdmin]

    def get(self, request):
        wid = self.get_workspace_id(request)
        workspace = get_object_or_404(Workspace, id=wid)
        usage = UsageRecord.get_current_period_usage(workspace)
        serializer = UsageRecordSerializer(usage)
        return Response(serializer.data)


# ─── Portal ──────────────────────────────────────────────────────────────────


class PortalView(WorkspaceScopedViewMixin, APIView):
    """POST /v1/billing/portal/ — returns Stripe billing portal URL."""
    permission_classes = [IsWorkspaceAdmin]

    def post(self, request):
        serializer = CreatePortalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wid = self.get_workspace_id(request)
        workspace = get_object_or_404(Workspace, id=wid)
        try:
            portal_url = BillingService.create_portal_session(
                workspace=workspace,
                return_url=serializer.validated_data["return_url"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"portal_url": portal_url})
