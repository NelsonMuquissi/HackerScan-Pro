"""
HackScan Pro — Billing Serializers.
"""
from rest_framework import serializers

from .models import Invoice, Plan, Subscription, UsageRecord


# ─── Read-only ───────────────────────────────────────────────────────────────


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "id", "name", "display_name",
            "price_monthly", "price_yearly", "currency",
            "features", "limits", "is_active",
        ]
        read_only_fields = fields


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id", "plan", "status", "billing_cycle",
            "current_period_start", "current_period_end",
            "cancel_at_period_end", "cancelled_at", "trial_end",
            "created_at",
        ]
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            "id", "stripe_invoice_id", "amount", "currency",
            "status", "pdf_url", "period_start", "period_end",
            "paid_at", "created_at",
        ]
        read_only_fields = fields


class UsageRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageRecord
        fields = [
            "id", "period_start", "period_end",
            "scans_count", "api_calls_count", "findings_count",
        ]
        read_only_fields = fields


# ─── Input ───────────────────────────────────────────────────────────────────


class CreateCheckoutSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()
    billing_cycle = serializers.ChoiceField(choices=["monthly", "yearly"])
    success_url = serializers.URLField()
    cancel_url = serializers.URLField()


class UpdateSubscriptionSerializer(serializers.Serializer):
    plan_id = serializers.UUIDField()


class CreatePortalSerializer(serializers.Serializer):
    return_url = serializers.URLField()
