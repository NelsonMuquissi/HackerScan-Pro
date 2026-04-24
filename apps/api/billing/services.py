"""
HackScan Pro — Billing Service (Stripe integration).

Handles:
  - Checkout session creation
  - Billing portal session creation
  - Idempotent webhook event dispatch (7 events)
  - Quota checking
"""
import logging
from django.db.models import F
from datetime import datetime, timezone as dt_timezone

import stripe
from django.conf import settings
from django.utils import timezone

from .models import (
    Invoice,
    InvoiceStatus,
    Plan,
    Subscription,
    SubscriptionStatus,
    UsageRecord,
)

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


class BillingService:
    """Stripe-backed billing operations."""

    # ─── Checkout ────────────────────────────────────────────────────────

    @staticmethod
    def create_checkout_session(
        workspace,
        plan: Plan,
        billing_cycle: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Creates a Stripe Checkout Session and returns the redirect URL."""
        price_id = (
            plan.stripe_price_monthly_id
            if billing_cycle == "monthly"
            else plan.stripe_price_yearly_id
        )

        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "workspace_id": str(workspace.id),
                "plan_id": str(plan.id),
                "billing_cycle": billing_cycle,
            },
        )
        return session.url

    @staticmethod
    def create_module_checkout_session(
        workspace,
        module_slug: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Creates a Stripe Checkout Session for a Security Module (Marketplace)."""
        session = stripe.checkout.Session.create(
            mode="payment",  # Modules are one-off or recurring? Let's assume one-off for now
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "workspace_id": str(workspace.id),
                "module_slug": module_slug,
                "type": "module_purchase",
            },
        )
        return session.url

    # ─── Portal ──────────────────────────────────────────────────────────

    @staticmethod
    def create_portal_session(workspace, return_url: str) -> str:
        """Creates a Stripe Billing Portal session and returns the URL."""
        try:
            subscription = workspace.subscription
        except Subscription.DoesNotExist:
            raise ValueError("Workspace has no active subscription.")

        if not subscription.stripe_customer_id:
            raise ValueError("No Stripe customer ID on file.")

        session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=return_url,
        )
        return session.url

    # ─── Webhook dispatch ────────────────────────────────────────────────

    @staticmethod
    def handle_webhook(payload: bytes, sig_header: str) -> None:
        """Verifies signature and dispatches to the appropriate handler."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET,
            )
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid webhook signature.")

        handlers = {
            "checkout.session.completed": BillingService._handle_checkout_completed,
            "invoice.payment_succeeded": BillingService._handle_payment_succeeded,
            "invoice.payment_failed": BillingService._handle_payment_failed,
            "invoice.upcoming": BillingService._handle_invoice_upcoming,
            "customer.subscription.updated": BillingService._handle_subscription_updated,
            "customer.subscription.deleted": BillingService._handle_subscription_deleted,
            "customer.subscription.trial_will_end": BillingService._handle_trial_will_end,
        }

        handler = handlers.get(event["type"])
        if handler:
            handler(event["data"]["object"])
        else:
            logger.info("Unhandled Stripe event type: %s", event["type"])

    # ─── Event handlers ──────────────────────────────────────────────────

    @staticmethod
    def _handle_checkout_completed(session: dict) -> None:
        """
        Idempotent: update_or_create keyed on workspace_id.
        Handles both Subscription checkouts and Marketplace Module purchases.
        """
        metadata = session.get("metadata", {})
        workspace_id = metadata.get("workspace_id")
        event_type = metadata.get("type", "subscription")

        if event_type == "module_purchase":
            module_slug = metadata.get("module_slug")
            from marketplace.models import SecurityModule, WorkspaceModule  # noqa: PLC0415
            from users.models import Workspace  # noqa: PLC0415
            
            workspace = Workspace.objects.get(id=workspace_id)
            module = SecurityModule.objects.get(slug=module_slug)
            
            # Activate module for workspace
            WorkspaceModule.objects.update_or_create(
                workspace=workspace,
                module=module,
                defaults={
                    "is_active": True,
                    "expires_at": None,  # Lifetime or based on module config
                }
            )
            logger.info("Module purchased: workspace=%s module=%s", workspace_id, module_slug)
            return

        if event_type == "ai_credits":
            package_slug = metadata.get("package_slug")
            from ai.models import CreditPackage  # noqa: PLC0415
            from ai.credit_service import CreditService  # noqa: PLC0415
            from users.models import Workspace  # noqa: PLC0415
            
            workspace = Workspace.objects.get(id=workspace_id)
            package = CreditPackage.objects.get(slug=package_slug)
            
            # Idempotency check via stripe_payment_intent_id is handled inside CreditService.credit
            # but we can do a quick check here too if desired.
            payment_intent = session.get("payment_intent")
            
            CreditService.credit(
                workspace=workspace,
                amount=package.total_credits,
                action=f"purchase_{package.slug}",
                credit_type="purchased",
                stripe_payment_intent_id=payment_intent,
            )
            logger.info("AI Credits purchased: workspace=%s package=%s amount=%s", 
                        workspace_id, package_slug, package.total_credits)
            return

        # Default: Subscription flow
        plan_id = metadata.get("plan_id")
        billing_cycle = metadata.get("billing_cycle")
        stripe_sub_id = session.get("subscription")

        stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)

        Subscription.objects.update_or_create(
            workspace_id=workspace_id,
            defaults={
                "plan_id": plan_id,
                "status": SubscriptionStatus.ACTIVE,
                "billing_cycle": billing_cycle,
                "stripe_subscription_id": stripe_sub_id,
                "stripe_customer_id": session["customer"],
                "current_period_start": datetime.fromtimestamp(
                    stripe_sub["current_period_start"], tz=dt_timezone.utc,
                ),
                "current_period_end": datetime.fromtimestamp(
                    stripe_sub["current_period_end"], tz=dt_timezone.utc,
                ),
            },
        )

        # Update workspace plan field for quick lookups
        from users.models import Workspace  # noqa: PLC0415

        plan = Plan.objects.get(id=plan_id)
        Workspace.objects.filter(id=workspace_id).update(plan=plan.name)
        logger.info("Checkout completed: workspace=%s plan=%s", workspace_id, plan.name)

    @staticmethod
    def _handle_payment_succeeded(invoice_data: dict) -> None:
        """Creates or updates an Invoice record on successful payment."""
        sub_id = invoice_data.get("subscription")
        subscription = None
        workspace = None

        if sub_id:
            subscription = Subscription.objects.filter(
                stripe_subscription_id=sub_id,
            ).select_related("workspace").first()
            if subscription:
                workspace = subscription.workspace

        if not workspace:
            logger.warning(
                "payment_succeeded: no workspace found for invoice %s",
                invoice_data.get("id"),
            )
            return

        Invoice.objects.update_or_create(
            stripe_invoice_id=invoice_data["id"],
            defaults={
                "workspace": workspace,
                "subscription": subscription,
                "amount": invoice_data["amount_paid"] / 100,
                "currency": invoice_data.get("currency", "usd").upper(),
                "status": InvoiceStatus.PAID,
                "pdf_url": invoice_data.get("invoice_pdf", ""),
                "period_start": datetime.fromtimestamp(
                    invoice_data["period_start"], tz=dt_timezone.utc,
                ) if invoice_data.get("period_start") else None,
                "period_end": datetime.fromtimestamp(
                    invoice_data["period_end"], tz=dt_timezone.utc,
                ) if invoice_data.get("period_end") else None,
                "paid_at": timezone.now(),
            },
        )

    @staticmethod
    def _handle_payment_failed(invoice_data: dict) -> None:
        """Marks subscription as past_due and records failed invoice."""
        sub_id = invoice_data.get("subscription")
        if sub_id:
            Subscription.objects.filter(
                stripe_subscription_id=sub_id,
            ).update(status=SubscriptionStatus.PAST_DUE)

        subscription = None
        workspace = None
        if sub_id:
            subscription = Subscription.objects.filter(
                stripe_subscription_id=sub_id,
            ).select_related("workspace").first()
            if subscription:
                workspace = subscription.workspace

        if workspace:
            Invoice.objects.update_or_create(
                stripe_invoice_id=invoice_data["id"],
                defaults={
                    "workspace": workspace,
                    "subscription": subscription,
                    "amount": invoice_data.get("amount_due", 0) / 100,
                    "currency": invoice_data.get("currency", "usd").upper(),
                    "status": InvoiceStatus.OPEN,
                    "pdf_url": invoice_data.get("invoice_pdf", ""),
                    "period_start": datetime.fromtimestamp(
                        invoice_data["period_start"], tz=dt_timezone.utc,
                    ) if invoice_data.get("period_start") else None,
                    "period_end": datetime.fromtimestamp(
                        invoice_data["period_end"], tz=dt_timezone.utc,
                    ) if invoice_data.get("period_end") else None,
                },
            )
        logger.warning("Payment failed for subscription %s", sub_id)

    @staticmethod
    def _handle_invoice_upcoming(invoice_data: dict) -> None:
        """
        Notifies the workspace owner that the next invoice is approaching.
        Triggered ~3 days before billing date by Stripe.
        """
        sub_id = invoice_data.get("subscription")
        if not sub_id:
            return

        subscription = Subscription.objects.filter(
            stripe_subscription_id=sub_id,
        ).select_related("workspace__owner").first()

        if not subscription:
            return

        # Delegate to the notification service (email)
        try:
            from notifications.services import NotificationService  # noqa: PLC0415

            NotificationService.send(
                user=subscription.workspace.owner,
                channel="email",
                template="billing/invoice_upcoming",
                context={
                    "workspace_name": subscription.workspace.name,
                    "amount": invoice_data.get("amount_due", 0) / 100,
                    "currency": invoice_data.get("currency", "usd").upper(),
                    "due_date": invoice_data.get("due_date"),
                },
            )
        except Exception:
            logger.exception("Failed to send invoice_upcoming notification")

    @staticmethod
    def _handle_subscription_updated(sub_data: dict) -> None:
        """Syncs plan/status/period changes from Stripe."""
        stripe_sub_id = sub_data["id"]
        subscription = Subscription.objects.filter(
            stripe_subscription_id=stripe_sub_id,
        ).first()

        if not subscription:
            logger.warning("subscription_updated: unknown sub %s", stripe_sub_id)
            return

        # Map Stripe status to our enum
        status_map = {
            "trialing": SubscriptionStatus.TRIALING,
            "active": SubscriptionStatus.ACTIVE,
            "past_due": SubscriptionStatus.PAST_DUE,
            "canceled": SubscriptionStatus.CANCELLED,
            "unpaid": SubscriptionStatus.UNPAID,
        }

        subscription.status = status_map.get(sub_data["status"], subscription.status)
        subscription.cancel_at_period_end = sub_data.get("cancel_at_period_end", False)
        subscription.current_period_start = datetime.fromtimestamp(
            sub_data["current_period_start"], tz=dt_timezone.utc,
        )
        subscription.current_period_end = datetime.fromtimestamp(
            sub_data["current_period_end"], tz=dt_timezone.utc,
        )
        subscription.save(update_fields=[
            "status", "cancel_at_period_end",
            "current_period_start", "current_period_end", "updated_at",
        ])

    @staticmethod
    def _handle_subscription_deleted(sub_data: dict) -> None:
        """Marks subscription as cancelled and downgrades workspace to free."""
        stripe_sub_id = sub_data["id"]
        subscription = Subscription.objects.filter(
            stripe_subscription_id=stripe_sub_id,
        ).select_related("workspace").first()

        if not subscription:
            return

        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = timezone.now()
        subscription.save(update_fields=["status", "cancelled_at", "updated_at"])

        # Downgrade workspace to free
        workspace = subscription.workspace
        workspace.plan = "free"
        workspace.save(update_fields=["plan", "updated_at"])

        # Assign the free plan
        free_plan = Plan.objects.filter(name="free", is_active=True).first()
        if free_plan:
            subscription.plan = free_plan
            subscription.save(update_fields=["plan_id", "updated_at"])

        logger.info("Subscription deleted: workspace=%s downgraded to free", workspace.slug)

    @staticmethod
    def _handle_trial_will_end(sub_data: dict) -> None:
        """
        Notifies workspace owner that the trial ends in ~3 days.
        Upsells conversion to a paid plan.
        """
        stripe_sub_id = sub_data["id"]
        subscription = Subscription.objects.filter(
            stripe_subscription_id=stripe_sub_id,
        ).select_related("workspace__owner", "plan").first()

        if not subscription:
            return

        try:
            from notifications.services import NotificationService  # noqa: PLC0415

            trial_end_ts = sub_data.get("trial_end")
            trial_end_dt = (
                datetime.fromtimestamp(trial_end_ts, tz=dt_timezone.utc)
                if trial_end_ts else None
            )

            NotificationService.send(
                user=subscription.workspace.owner,
                channel="email",
                template="billing/trial_will_end",
                context={
                    "workspace_name": subscription.workspace.name,
                    "plan_name": subscription.plan.display_name,
                    "trial_end_date": trial_end_dt,
                    "upgrade_url": f"{settings.FRONTEND_URL}/billing/upgrade/",
                },
            )
        except Exception:
            logger.exception("Failed to send trial_will_end notification")

    # ─── Quota ───────────────────────────────────────────────────────────

    @staticmethod
    def check_quota(workspace, action: str) -> tuple[bool, str]:
        """
        Checks whether the workspace can perform the given action.
        Returns (allowed, reason). Never raises — always returns a tuple.

        If the workspace has no active subscription, free-plan limits apply
        rather than blocking the user entirely.
        """
        from scans.models import ScanTarget  # noqa: PLC0415 — lazy to avoid circular

        try:
            subscription = workspace.subscription
            plan = subscription.plan
            limits = plan.limits
        except Subscription.DoesNotExist:
            # No paid subscription → apply free-plan limits if one exists,
            # otherwise grant access with a sensible default cap.
            free_plan = Plan.objects.filter(name="free", is_active=True).first()
            if free_plan:
                limits = free_plan.limits
            else:
                # Fallback: a sane default so the product doesn't hard-block everyone
                limits = {"scans_per_month": 5, "targets": 3, "api_calls_per_month": 100}

        if action == "create_scan":
            limit = limits.get("scans_per_month")
            if limit is None or limit == -1:  # unlimited
                return True, ""
            usage = UsageRecord.get_current_period_usage(workspace)
            if usage.scans_count >= limit:
                return False, f"Limite de {limit} scans/mês atingido."

        elif action == "schedule_scan":
            limit = limits.get("max_scheduled_scans", 0)
            if limit == -1:
                return True, ""
            from scans.models import ScheduledScan # noqa: PLC0415
            current_schedules = ScheduledScan.objects.filter(target__workspace=workspace, is_active=True).count()
            if current_schedules >= limit:
                return False, f"Seu plano permite apenas {limit} scans agendados simultâneos."

        elif action == "api_access":
            allowed = limits.get("allow_api_access", False)
            if not allowed:
                return False, "Acesso à API não disponível no seu plano atual."

        elif action == "create_target":
            limit = limits.get("targets")
            if limit is None or limit == -1:
                return True, ""
            target_count = ScanTarget.objects.filter(workspace=workspace).count()
            if target_count >= limit:
                return False, f"Limite de {limit} targets atingido."
        elif action == "api_call":
            limit = limits.get("api_calls_per_month")
            if not limit or limit == -1:
                return True, ""
            usage = UsageRecord.get_current_period_usage(workspace)
            if usage.api_calls_count >= limit:
                return False, f"Limite de {limit} API calls/mês atingido."

        elif action == "create_bounty":
            allowed = limits.get("allow_bounty_programs", False)
            if not allowed:
                return False, "Programas de Bug Bounty não estão disponíveis no seu plano atual."
            
            limit = limits.get("max_bounty_programs", 0)
            if limit != -1:
                from bounty.models import BountyProgram # noqa: PLC0415
                current_programs = BountyProgram.objects.filter(workspace=workspace).count()
                if current_programs >= limit:
                    return False, f"Seu plano permite apenas {limit} programas de Bug Bounty."

        return True, ""

    @staticmethod
    def increment_usage(workspace, field_name: str, increment: int = 1) -> None:
        """
        Increments a given counter on the workspace's current UsageRecord.
        Safe for use in high-concurrency environments (uses F expressions).
        """
        usage = UsageRecord.get_current_period_usage(workspace)
        if hasattr(usage, field_name):
            UsageRecord.objects.filter(id=usage.id).update(
                **{field_name: F(field_name) + increment}
            )
            # Update the local object just in case it's used in the same request
            current_val = getattr(usage, field_name)
            setattr(usage, field_name, current_val + increment)
