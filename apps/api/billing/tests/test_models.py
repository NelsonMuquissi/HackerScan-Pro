"""
Tests for billing.models — Plan, Subscription, Invoice, UsageRecord.
"""
import pytest
from django.db import IntegrityError
from django.utils import timezone

from billing.models import Plan, Subscription, UsageRecord


# ─── Plan ────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPlan:
    def test_plan_creation_with_limits(self, free_plan):
        assert free_plan.name == "free"
        assert free_plan.limits["scans_per_month"] == 5
        assert free_plan.limits["targets"] == 1
        assert free_plan.is_active is True

    def test_plan_str(self, free_plan):
        assert "Free" in str(free_plan)

    def test_plan_name_unique(self, free_plan):
        with pytest.raises(IntegrityError):
            Plan.objects.create(
                name="free",
                display_name="Free Duplicate",
                limits={},
            )


# ─── Subscription ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSubscription:
    def test_subscription_creation(self, subscription):
        assert subscription.status == "active"
        assert subscription.billing_cycle == "monthly"
        assert subscription.plan.name == "free"

    def test_subscription_str(self, subscription):
        text = str(subscription)
        assert "test-workspace" in text
        assert "free" in text
        assert "active" in text

    def test_subscription_one_to_one_workspace(self, subscription, workspace, pro_plan):
        """Cannot create a second subscription for the same workspace."""
        now = timezone.now()
        with pytest.raises(IntegrityError):
            Subscription.objects.create(
                workspace=workspace,
                plan=pro_plan,
                status="active",
                billing_cycle="monthly",
                current_period_start=now,
                current_period_end=now + timezone.timedelta(days=30),
            )


# ─── UsageRecord ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestUsageRecord:
    def test_usage_record_creation(self, workspace, subscription):
        usage = UsageRecord.get_current_period_usage(workspace)
        assert usage.scans_count == 0
        assert usage.api_calls_count == 0
        assert usage.findings_count == 0

    def test_usage_record_get_current_period_returns_same_record(
        self, workspace, subscription,
    ):
        usage1 = UsageRecord.get_current_period_usage(workspace)
        usage2 = UsageRecord.get_current_period_usage(workspace)
        assert usage1.id == usage2.id

    def test_usage_record_unique_constraint(self, workspace, subscription):
        usage = UsageRecord.get_current_period_usage(workspace)
        with pytest.raises(IntegrityError):
            UsageRecord.objects.create(
                workspace=workspace,
                period_start=usage.period_start,
                period_end=usage.period_end,
            )

    def test_usage_record_without_subscription(self, workspace):
        """Falls back to calendar-month boundaries when no subscription."""
        usage = UsageRecord.get_current_period_usage(workspace)
        assert usage.period_start.day == 1
        assert usage.scans_count == 0
