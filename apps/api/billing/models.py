"""
HackScan Pro — Billing Models.

Tables:
  - Plan           (subscription plans: free, pro, team, enterprise)
  - Subscription   (workspace ↔ plan binding via Stripe)
  - Invoice        (payment records synced from Stripe)
  - UsageRecord    (per-period usage counters for quota enforcement)
"""
from django.db import models
from django.utils import timezone

from core.models import UUIDModel, TimestampedModel
from users.models import Workspace


# ─── Plan ────────────────────────────────────────────────────────────────────


class Plan(UUIDModel):
    """
    Subscription tier definition.
    Limits JSONB example: { "scans_per_month": 5, "targets": 1, "users": 1, "api_access": false }
    """
    name = models.CharField(max_length=100, unique=True)       # free, pro, team, enterprise
    display_name = models.CharField(max_length=255)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")
    features = models.JSONField(default=dict)
    limits = models.JSONField(default=dict)
    stripe_price_monthly_id = models.CharField(max_length=255, blank=True, default="")
    stripe_price_yearly_id = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "plans"

    def __str__(self) -> str:
        return f"{self.display_name} ({self.name})"


# ─── Subscription ────────────────────────────────────────────────────────────


class SubscriptionStatus(models.TextChoices):
    TRIALING = "trialing", "Trialing"
    ACTIVE = "active", "Active"
    PAST_DUE = "past_due", "Past Due"
    CANCELLED = "cancelled", "Cancelled"
    UNPAID = "unpaid", "Unpaid"


class BillingCycle(models.TextChoices):
    MONTHLY = "monthly", "Monthly"
    YEARLY = "yearly", "Yearly"


class Subscription(UUIDModel, TimestampedModel):
    """
    Links a Workspace to a Plan via Stripe.
    One active subscription per workspace (enforced at service level).
    """
    workspace = models.OneToOneField(
        Workspace, on_delete=models.RESTRICT, related_name="subscription"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(
        max_length=50,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.ACTIVE,
    )
    billing_cycle = models.CharField(
        max_length=20, choices=BillingCycle.choices, default=BillingCycle.MONTHLY,
    )
    stripe_subscription_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=255, blank=True, default="")
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "subscriptions"
        indexes = [
            models.Index(fields=["workspace"], name="idx_subscriptions_workspace"),
            models.Index(fields=["stripe_subscription_id"], name="idx_subscriptions_stripe"),
        ]

    def __str__(self) -> str:
        return f"Subscription<{self.workspace.slug} / {self.plan.name} / {self.status}>"


# ─── Invoice ─────────────────────────────────────────────────────────────────


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    OPEN = "open", "Open"
    PAID = "paid", "Paid"
    VOID = "void", "Void"
    UNCOLLECTIBLE = "uncollectible", "Uncollectible"


class Invoice(UUIDModel):
    """
    Invoice synced from Stripe — immutable after creation.
    """
    workspace = models.ForeignKey(
        Workspace, on_delete=models.RESTRICT, related_name="invoices"
    )
    subscription = models.ForeignKey(
        Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices"
    )
    stripe_invoice_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=50, choices=InvoiceStatus.choices)
    pdf_url = models.TextField(blank=True, default="")
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "invoices"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Invoice<{self.stripe_invoice_id} / {self.status}>"


# ─── UsageRecord ─────────────────────────────────────────────────────────────


class UsageRecord(UUIDModel):
    """
    Per-period usage counters for quota enforcement.
    One record per workspace per billing period.
    """
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="usage_records"
    )
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    scans_count = models.IntegerField(default=0)
    api_calls_count = models.IntegerField(default=0)
    findings_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "usage_records"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "period_start"],
                name="uq_usage_workspace_period",
            ),
        ]

    def __str__(self) -> str:
        return f"Usage<{self.workspace.slug} / {self.period_start.date()}>"

    @classmethod
    def get_current_period_usage(cls, workspace: Workspace) -> "UsageRecord":
        """
        Returns (or creates) the usage record for the workspace's current
        billing period. Falls back to calendar-month boundaries if no
        active subscription exists.
        """
        now = timezone.now()
        try:
            sub = workspace.subscription
            period_start = sub.current_period_start
            period_end = sub.current_period_end
        except Subscription.DoesNotExist:
            # Fallback: calendar month
            period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                period_end = period_start.replace(year=now.year + 1, month=1)
            else:
                period_end = period_start.replace(month=now.month + 1)

        record, _created = cls.objects.get_or_create(
            workspace=workspace,
            period_start=period_start,
            defaults={"period_end": period_end},
        )
        return record
