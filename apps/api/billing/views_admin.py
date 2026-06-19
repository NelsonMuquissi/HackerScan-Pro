"""
HackScan Pro — Billing Admin Views.
"""
from rest_framework import generics, permissions, status, viewsets, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsSuperAdmin
from .models import Plan, Subscription, UsageRecord, Invoice
from .serializers import PlanSerializer, SubscriptionSerializer, UsageRecordSerializer, InvoiceSerializer

# ─── Serializers ─────────────────────────────────────────────────────────────

class GlobalAdminPlanSerializer(PlanSerializer):
    class Meta(PlanSerializer.Meta):
        read_only_fields = ["id", "created_at"]

class GlobalAdminSubscriptionSerializer(SubscriptionSerializer):
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)
    workspace_slug = serializers.CharField(source="workspace.slug", read_only=True)
    owner_email = serializers.EmailField(source="workspace.owner.email", read_only=True)

    class Meta(SubscriptionSerializer.Meta):
        fields = SubscriptionSerializer.Meta.fields + ["workspace_name", "workspace_slug", "owner_email"]

class GlobalAdminUsageRecordSerializer(UsageRecordSerializer):
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)
    
    class Meta(UsageRecordSerializer.Meta):
        fields = UsageRecordSerializer.Meta.fields + ["workspace_name"]

# ─── Views ───────────────────────────────────────────────────────────────────

class GlobalAdminPlanViewSet(viewsets.ModelViewSet):
    """
    CRUD for subscription plans.
    """
    queryset = Plan.objects.all().order_by("price_monthly")
    serializer_class = GlobalAdminPlanSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

class GlobalAdminSubscriptionListView(generics.ListAPIView):
    """
    Monitor all active subscriptions across the platform.
    """
    queryset = Subscription.objects.select_related("workspace", "workspace__owner", "plan").all().order_by("-created_at")
    serializer_class = GlobalAdminSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

class GlobalAdminUsageListView(generics.ListAPIView):
    """
    Monitor usage records across all workspaces.
    """
    queryset = UsageRecord.objects.select_related("workspace").all().order_by("-period_start")
    serializer_class = GlobalAdminUsageRecordSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

class GlobalAdminInvoiceListView(generics.ListAPIView):
    """
    Monitor all invoices.
    """
    queryset = Invoice.objects.select_related("workspace").all().order_by("-created_at")
    serializer_class = InvoiceSerializer # We can use the standard one, maybe add workspace info
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
