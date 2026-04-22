"""
Tests for billing.services — BillingService (Stripe mocked).
"""
from datetime import timezone as dt_timezone
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from billing.models import Invoice, Subscription, SubscriptionStatus, UsageRecord
from billing.services import BillingService


# ─── Checkout ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCheckoutSession:
    @patch("billing.services.stripe.checkout.Session.create")
    def test_create_checkout_session_calls_stripe(
        self, mock_create, workspace, pro_plan,
    ):
        mock_create.return_value = MagicMock(url="https://checkout.stripe.com/test")

        url = BillingService.create_checkout_session(
            workspace=workspace,
            plan=pro_plan,
            billing_cycle="monthly",
            success_url="https://app.test/success",
            cancel_url="https://app.test/cancel",
        )

        assert url == "https://checkout.stripe.com/test"
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["mode"] == "subscription"
        assert call_kwargs["metadata"]["workspace_id"] == str(workspace.id)


# ─── Webhook Signature ──────────────────────────────────────────────────────


@pytest.mark.django_db
class TestWebhookSignature:
    @patch("billing.services.stripe.Webhook.construct_event")
    def test_handle_webhook_invalid_signature_raises(self, mock_construct):
        import stripe  # noqa: PLC0415

        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            "bad sig", "sig_header",
        )

        with pytest.raises(ValueError, match="Invalid webhook signature"):
            BillingService.handle_webhook(b"payload", "bad_sig")


# ─── checkout.session.completed ──────────────────────────────────────────────


@pytest.mark.django_db
class TestHandleCheckoutCompleted:
    @patch("billing.services.stripe.Subscription.retrieve")
    def test_creates_subscription(self, mock_retrieve, workspace, pro_plan):
        now_ts = int(timezone.now().timestamp())
        mock_retrieve.return_value = {
            "current_period_start": now_ts,
            "current_period_end": now_ts + 2_592_000,
        }

        session = {
            "metadata": {
                "workspace_id": str(workspace.id),
                "plan_id": str(pro_plan.id),
                "billing_cycle": "monthly",
            },
            "subscription": "sub_test_123",
            "customer": "cus_test_456",
        }

        BillingService._handle_checkout_completed(session)

        sub = Subscription.objects.get(workspace=workspace)
        assert sub.status == SubscriptionStatus.ACTIVE
        assert sub.stripe_subscription_id == "sub_test_123"
        assert sub.stripe_customer_id == "cus_test_456"
        assert sub.plan == pro_plan

    @patch("billing.services.stripe.Subscription.retrieve")
    def test_idempotent_on_duplicate(self, mock_retrieve, workspace, pro_plan):
        """Calling twice with the same workspace_id should update, not create two."""
        now_ts = int(timezone.now().timestamp())
        mock_retrieve.return_value = {
            "current_period_start": now_ts,
            "current_period_end": now_ts + 2_592_000,
        }

        session = {
            "metadata": {
                "workspace_id": str(workspace.id),
                "plan_id": str(pro_plan.id),
                "billing_cycle": "monthly",
            },
            "subscription": "sub_test_123",
            "customer": "cus_test_456",
        }

        BillingService._handle_checkout_completed(session)
        BillingService._handle_checkout_completed(session)

        assert Subscription.objects.filter(workspace=workspace).count() == 1


# ─── invoice.payment_failed ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestHandlePaymentFailed:
    def test_updates_subscription_status(self, subscription):
        subscription.stripe_subscription_id = "sub_fail_test"
        subscription.save(update_fields=["stripe_subscription_id"])

        now_ts = int(timezone.now().timestamp())
        invoice_data = {
            "id": "in_fail_test",
            "subscription": "sub_fail_test",
            "amount_due": 2900,
            "currency": "usd",
            "invoice_pdf": "",
            "period_start": now_ts,
            "period_end": now_ts + 2_592_000,
        }

        BillingService._handle_payment_failed(invoice_data)

        subscription.refresh_from_db()
        assert subscription.status == SubscriptionStatus.PAST_DUE

        invoice = Invoice.objects.get(stripe_invoice_id="in_fail_test")
        assert invoice.status == "open"


# ─── customer.subscription.deleted ───────────────────────────────────────────


@pytest.mark.django_db
class TestHandleSubscriptionDeleted:
    def test_cancels_and_downgrades(self, subscription, free_plan):
        subscription.stripe_subscription_id = "sub_delete_test"
        subscription.save(update_fields=["stripe_subscription_id"])

        sub_data = {"id": "sub_delete_test"}

        BillingService._handle_subscription_deleted(sub_data)

        subscription.refresh_from_db()
        assert subscription.status == SubscriptionStatus.CANCELLED
        assert subscription.cancelled_at is not None

        subscription.workspace.refresh_from_db()
        assert subscription.workspace.plan == "free"


# ─── Quota ───────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCheckQuota:
    def test_allows_within_limit(self, workspace, subscription):
        allowed, reason = BillingService.check_quota(workspace, "create_scan")
        assert allowed is True
        assert reason == ""

    def test_denies_when_limit_reached(self, workspace, subscription):
        # Fill up usage to the limit (free plan = 5 scans)
        usage = UsageRecord.get_current_period_usage(workspace)
        usage.scans_count = 5
        usage.save(update_fields=["scans_count"])

        allowed, reason = BillingService.check_quota(workspace, "create_scan")
        assert allowed is False
        assert "5" in reason

    def test_allows_unlimited_plan(self, workspace, subscription, pro_plan):
        # Switch to pro plan (scans_per_month = -1 = unlimited)
        subscription.plan = pro_plan
        subscription.save(update_fields=["plan_id"])

        allowed, reason = BillingService.check_quota(workspace, "create_scan")
        assert allowed is True
        assert reason == ""

    def test_no_subscription_returns_false(self, workspace):
        """Workspace without subscription → not allowed."""
        allowed, reason = BillingService.check_quota(workspace, "create_scan")
        assert allowed is False
        assert "subscription" in reason.lower()
