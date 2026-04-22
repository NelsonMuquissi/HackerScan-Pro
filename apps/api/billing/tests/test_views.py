"""
Tests for billing.views — API endpoints.
"""
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status


# ─── Plans ───────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPlanListView:
    def test_list_plans_returns_active_plans(self, api_client, free_plan, pro_plan):
        url = reverse("billing-plans")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Pagination wrapper
        results = data.get("results", data)
        names = [p["name"] for p in results]
        assert "free" in names
        assert "pro" in names

    def test_plans_are_public(self, api_client, free_plan):
        """Plans endpoint does not require authentication."""
        url = reverse("billing-plans")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK


# ─── Subscription ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestSubscriptionView:
    def test_get_subscription_returns_current(
        self, auth_client, workspace, subscription,
    ):
        url = reverse("billing-subscription")
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "active"
        assert response.json()["plan"]["name"] == "free"

    def test_get_subscription_404_when_none(self, auth_client, workspace):
        url = reverse("billing-subscription")
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("billing.services.BillingService.create_checkout_session")
    def test_create_subscription_returns_checkout_url(
        self, mock_checkout, auth_client, workspace, pro_plan,
    ):
        mock_checkout.return_value = "https://checkout.stripe.com/test"
        url = reverse("billing-subscription")

        response = auth_client.post(url, data={
            "plan_id": str(pro_plan.id),
            "billing_cycle": "monthly",
            "success_url": "https://app.test/success",
            "cancel_url": "https://app.test/cancel",
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["checkout_url"] == "https://checkout.stripe.com/test"

    @patch("billing.views.stripe.Subscription.modify")
    def test_cancel_subscription_sets_cancel_at_period_end(
        self, mock_modify, auth_client, workspace, subscription,
    ):
        subscription.stripe_subscription_id = "sub_cancel_test"
        subscription.save(update_fields=["stripe_subscription_id"])

        url = reverse("billing-subscription")
        response = auth_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        subscription.refresh_from_db()
        assert subscription.cancel_at_period_end is True

    def test_billing_endpoints_require_authentication(self, api_client, workspace):
        """Subscription, invoices, usage, portal require auth."""
        for name in ["billing-subscription", "billing-invoices", "billing-usage"]:
            url = reverse(name)
            response = api_client.get(url)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
                f"{name} should require auth"
            )


# ─── Webhook ─────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestStripeWebhook:
    def test_webhook_no_auth_required(self, api_client):
        """Webhook endpoint should not require JWT auth (returns 400, not 401)."""
        url = reverse("billing-stripe-webhook")
        response = api_client.post(url, data=b"invalid", content_type="application/json")
        # 400 = invalid signature is the expected failure, NOT 401
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ─── Usage ───────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestUsageView:
    def test_get_usage_returns_current_period(
        self, auth_client, workspace, subscription,
    ):
        url = reverse("billing-usage")
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["scans_count"] == 0
        assert response.json()["api_calls_count"] == 0


# ─── Invoices ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestInvoiceListView:
    def test_list_invoices_empty(self, auth_client, workspace):
        url = reverse("billing-invoices")
        response = auth_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        results = response.json().get("results", response.json())
        assert len(results) == 0
