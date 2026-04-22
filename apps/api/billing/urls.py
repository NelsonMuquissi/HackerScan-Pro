"""
HackScan Pro — Billing URL Configuration.
"""
from django.urls import path

from . import views, webhooks

urlpatterns = [
    # Plans (public)
    path("plans/", views.PlanListView.as_view(), name="billing-plans"),

    # Subscription management
    path("subscription/", views.SubscriptionView.as_view(), name="billing-subscription"),

    # Invoices
    path("invoices/", views.InvoiceListView.as_view(), name="billing-invoices"),

    # Usage
    path("usage/", views.UsageView.as_view(), name="billing-usage"),

    # Stripe portal
    path("portal/", views.PortalView.as_view(), name="billing-portal"),

    # Stripe webhook (no auth — signature verified internally)
    path("webhooks/stripe/", webhooks.stripe_webhook_view, name="billing-stripe-webhook"),
]
