"""
HackScan Pro — AI Credit Service.

Handles all credit-related business logic:
  - check_balance: verify workspace has sufficient credits
  - debit:         atomically debit credits (subscription → purchased → bonus)
  - credit:        add credits to a wallet bucket
  - is_first_use:  check if this is the first time a workspace uses an action
  - grant_achievement: idempotently unlock an achievement and award credits
  - grant_monthly_credits: idempotently grant monthly plan credits
  - _check_alerts: fire low/zero balance notifications

All wallet mutations use SELECT FOR UPDATE for thread safety.
"""
import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import (
    AITransaction,
    AIWallet,
    Achievement,
    MonthlyCreditGrant,
    WorkspaceAchievement,
)

logger = logging.getLogger(__name__)


# ─── Exceptions ──────────────────────────────────────────────────────────────


class InsufficientCreditsError(Exception):
    """Raised when a workspace lacks credits for an AI action."""

    def __init__(self, needed: int, available: int, action: str):
        self.needed = needed
        self.available = available
        self.action = action
        self.shortfall = needed - available
        super().__init__(
            f"Créditos insuficientes para '{action}': "
            f"necessário {needed}, disponível {available}"
        )


# ─── Cost table ──────────────────────────────────────────────────────────────


AI_ACTION_COSTS: dict[str, int] = {
    "explain_finding": 10,
    "explain_finding_first_use": 0,
    "explain_finding_express": 20,
    "generate_report_pdf": 60,
    "generate_report_executive": 90,
    "ai_forecaster": 35,
    "attack_chains": 50,
    "remediation_code": 15,
    "chat_message": 5,
    "chat_message_express": 10,
    "compliance_report_lgpd": 150,
    "compliance_report_iso": 200,
    "compliance_report_pci": 180,
}

# ─── Anthropic pricing (per 1M tokens) ──────────────────────────────────────

ANTHROPIC_INPUT_CPM = Decimal("3.00")
ANTHROPIC_OUTPUT_CPM = Decimal("15.00")
REVENUE_PER_CREDIT = Decimal("0.01")


# ─── CreditService ──────────────────────────────────────────────────────────


class CreditService:
    """
    Stateless service for all AI credit operations.
    Every wallet mutation is wrapped in SELECT FOR UPDATE.
    """

    # ── Cost lookup ──────────────────────────────────────────────────────

    @classmethod
    def get_cost(cls, action: str, express: bool = False) -> int:
        """Return credit cost for an action. Express = 2× for eligible actions."""
        if express:
            express_key = f"{action}_express"
            if express_key in AI_ACTION_COSTS:
                return AI_ACTION_COSTS[express_key]
        return AI_ACTION_COSTS.get(action, 10)

    # ── Balance check ────────────────────────────────────────────────────

    @classmethod
    def check_balance(
        cls,
        workspace,
        action: str,
        express: bool = False,
        user=None,
    ) -> tuple[bool, int, int]:
        """
        Check whether workspace can afford an action.
        Returns: (has_balance, cost, current_balance)
        Admins and SuperAdmins always have balance.
        """
        from users.models import UserRole # noqa: PLC0415
        if user and user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
             return True, 0, 999999

        cost = cls.get_cost(action, express)
        if cost == 0:
            return True, 0, 0

        try:
            wallet = AIWallet.objects.get(workspace=workspace)
            return wallet.balance_total >= cost, cost, wallet.balance_total
        except AIWallet.DoesNotExist:
            return False, cost, 0

    # ── Debit ────────────────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def debit(
        cls,
        workspace,
        user,
        action: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        model_used: str = "claude-3-5-sonnet-20241022",
        reference_type: str = "",
        reference_id=None,
        was_cached: bool = False,
        express: bool = False,
        cache_key: str = "",
    ) -> AITransaction:
        """
        Atomically debit credits from wallet.
        Consumption order: subscription → purchased → bonus.
        Uses SELECT FOR UPDATE for thread safety.
        Admins and SuperAdmins skip the debit.
        """
        from users.models import UserRole # noqa: PLC0415
        if user and user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
             # Create a record of the use but with 0 cost
             was_cached = True # effective bypass
             cost = 0
        else:
             cost = 0 if was_cached else cls.get_cost(action, express)

        wallet, _created = AIWallet.objects.select_for_update().get_or_create(
            workspace=workspace,
            defaults={
                "balance_subscription": 0,
                "balance_purchased": 0,
                "balance_bonus": 0,
            },
        )

        if not was_cached and cost > 0 and wallet.balance_total < cost:
            raise InsufficientCreditsError(cost, wallet.balance_total, action)

        balance_before = wallet.balance_total

        # ── Consume in order: subscription → purchased → bonus ──
        debit_sub = debit_purch = debit_bonus = 0
        if not was_cached and cost > 0:
            remaining = cost

            # 1. Subscription credits first (they expire)
            use_sub = min(remaining, wallet.balance_subscription)
            wallet.balance_subscription -= use_sub
            debit_sub = use_sub
            remaining -= use_sub

            # 2. Purchased credits second (never expire)
            if remaining > 0:
                use_purch = min(remaining, wallet.balance_purchased)
                wallet.balance_purchased -= use_purch
                debit_purch = use_purch
                remaining -= use_purch

            # 3. Bonus credits last
            if remaining > 0:
                use_bonus = min(remaining, wallet.balance_bonus)
                wallet.balance_bonus -= use_bonus
                debit_bonus = use_bonus

            wallet.lifetime_credits_used += cost
            wallet.save(update_fields=[
                "balance_subscription",
                "balance_purchased",
                "balance_bonus",
                "lifetime_credits_used",
                "updated_at",
            ])

        # ── Calculate financial metrics ──
        cost_usd = (
            Decimal(tokens_input) * ANTHROPIC_INPUT_CPM
            + Decimal(tokens_output) * ANTHROPIC_OUTPUT_CPM
        ) / Decimal("1000000")

        revenue_usd = Decimal(cost) * REVENUE_PER_CREDIT
        margin_pct = (
            ((revenue_usd - cost_usd) / revenue_usd * 100)
            if revenue_usd > 0
            else Decimal("0")
        )

        tx = AITransaction.objects.create(
            workspace=workspace,
            user=user,
            type="debit",
            action=action,
            amount=cost,
            balance_before=balance_before,
            balance_after=wallet.balance_total,
            debit_from_subscription=debit_sub,
            debit_from_purchased=debit_purch,
            debit_from_bonus=debit_bonus,
            mode="express" if express else "standard",
            mode_multiplier=Decimal("2.0") if express else Decimal("1.0"),
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            model_used=model_used,
            cost_usd=cost_usd,
            revenue_usd=revenue_usd,
            margin_pct=margin_pct,
            was_cached=was_cached,
            cache_hit_key=cache_key if was_cached else "",
            reference_type=reference_type,
            reference_id=reference_id,
        )

        # Update lifetime revenue
        if not was_cached and revenue_usd > 0:
            wallet.lifetime_revenue_usd += revenue_usd
            wallet.save(update_fields=["lifetime_revenue_usd"])

        # Check low balance alerts
        if not was_cached and cost > 0:
            cls._check_alerts(workspace, wallet)

        logger.info(
            "ai.credit.debit",
            extra={
                "workspace_id": str(workspace.id),
                "action": action,
                "cost": cost,
                "balance_after": wallet.balance_total,
                "margin_pct": float(margin_pct),
                "was_cached": was_cached,
            },
        )

        return tx

    # ── Credit ───────────────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def credit(
        cls,
        workspace,
        amount: int,
        action: str,
        credit_type: str = "bonus",
        user=None,
        stripe_payment_intent_id: str = "",
    ) -> AITransaction:
        """
        Add credits to the wallet atomically.
        credit_type must be one of: subscription, purchased, bonus.
        """
        wallet, _created = AIWallet.objects.select_for_update().get_or_create(
            workspace=workspace,
            defaults={},
        )

        balance_before = wallet.balance_total

        if credit_type == "subscription":
            wallet.balance_subscription += amount
        elif credit_type == "purchased":
            wallet.balance_purchased += amount
        else:
            wallet.balance_bonus += amount

        wallet.lifetime_credits_granted += amount
        # Reset alert flags when credits are added
        wallet.low_balance_alert_sent_at = None
        wallet.zero_balance_alert_sent_at = None
        wallet.save(update_fields=[
            "balance_subscription",
            "balance_purchased",
            "balance_bonus",
            "lifetime_credits_granted",
            "low_balance_alert_sent_at",
            "zero_balance_alert_sent_at",
            "updated_at",
        ])

        tx = AITransaction.objects.create(
            workspace=workspace,
            user=user,
            type="credit",
            action=action,
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance_total,
            stripe_payment_intent_id=stripe_payment_intent_id,
        )

        logger.info(
            "ai.credit.credit",
            extra={
                "workspace_id": str(workspace.id),
                "action": action,
                "amount": amount,
                "credit_type": credit_type,
                "balance_after": wallet.balance_total,
            },
        )

        return tx

    # ── First use check ──────────────────────────────────────────────────

    @classmethod
    def is_first_use(cls, workspace, action: str) -> bool:
        """Check if this is the workspace's first time using a given action."""
        return not AITransaction.objects.filter(
            workspace=workspace,
            type="debit",
            action=action,
        ).exists()

    # ── Achievement grant ────────────────────────────────────────────────

    @classmethod
    def grant_achievement(cls, workspace, achievement_slug: str) -> bool:
        """
        Idempotently unlock an achievement for a workspace.
        Awards bonus credits if newly unlocked.
        Returns True if the achievement was just unlocked now.
        """
        achievement = Achievement.objects.filter(
            slug=achievement_slug, is_active=True,
        ).first()
        if not achievement:
            return False

        _, created = WorkspaceAchievement.objects.get_or_create(
            workspace=workspace,
            achievement=achievement,
            defaults={"credits_awarded": achievement.credits},
        )

        if created and achievement.credits > 0:
            cls.credit(
                workspace=workspace,
                amount=achievement.credits,
                action=f"bonus_achievement_{achievement_slug}",
                credit_type="bonus",
            )

        if created:
            logger.info(
                "ai.achievement.unlocked",
                extra={
                    "workspace_id": str(workspace.id),
                    "achievement": achievement_slug,
                    "credits": achievement.credits,
                },
            )

        return created

    # ── Monthly grant ────────────────────────────────────────────────────

    @classmethod
    @transaction.atomic
    def grant_monthly_credits(cls, workspace, subscription) -> None:
        """
        Grant monthly plan credits. Idempotent via MonthlyCreditGrant unique constraint.
        Resets subscription balance to the new grant amount (old credits don't roll over
        unless loyalty rollover is enabled).
        """
        plan = subscription.plan
        monthly_credits = plan.features.get("ai_credits_monthly", 0)
        if monthly_credits <= 0:
            return

        period_start = subscription.current_period_start
        period_end = subscription.current_period_end

        # Idempotency: check if grant already exists for this period
        if MonthlyCreditGrant.objects.filter(
            workspace=workspace,
            period_start=period_start,
        ).exists():
            logger.info(
                "ai.monthly_grant.skipped_duplicate",
                extra={
                    "workspace_id": str(workspace.id),
                    "period_start": str(period_start),
                },
            )
            return

        wallet, _ = AIWallet.objects.select_for_update().get_or_create(
            workspace=workspace,
            defaults={},
        )

        # Calculate rollover (20% of unused subscription credits for loyal users)
        rollover = 0
        if wallet.consecutive_months_active >= 6:
            rollover = min(
                int(wallet.balance_subscription * Decimal("0.20")),
                monthly_credits,  # max rollover = 1 month of credits
            )

        # Update wallet metrics (excluding balance which is handled by .credit())
        wallet.lifetime_credits_granted += monthly_credits
        wallet.consecutive_months_active += 1
        wallet.rollover_credits = rollover
        wallet.save(update_fields=[
            "lifetime_credits_granted",
            "consecutive_months_active",
            "rollover_credits",
            "updated_at",
        ])

        # Record the grant for audit & idempotency
        MonthlyCreditGrant.objects.create(
            workspace=workspace,
            subscription=subscription,
            period_start=period_start,
            period_end=period_end,
            credits_granted=monthly_credits,
            rollover_added=rollover,
        )

        # Perform the actual credit operation (this handles balance update and transaction record)
        # We use 'subscription' type so it sets/adds to balance_subscription
        # Note: If we want to RESET the balance instead of adding, we should handle that in credit()
        # or clear it here. For subscription grants, it's usually a reset to (monthly + rollover).
        
        # Clear existing subscription balance before applying the new grant
        wallet.balance_subscription = 0
        wallet.save(update_fields=["balance_subscription"])

        cls.credit(
            workspace=workspace,
            amount=monthly_credits + rollover,
            action="monthly_grant",
            credit_type="subscription",
        )

        logger.info(
            "ai.monthly_grant.processed",
            extra={
                "workspace_id": str(workspace.id),
                "credits_granted": monthly_credits,
                "rollover": rollover,
                "new_balance": wallet.balance_total,
            },
        )

    # ── Alert checks ─────────────────────────────────────────────────────

    @classmethod
    def _check_alerts(cls, workspace, wallet) -> None:
        """Check and fire low/zero balance alerts. Non-blocking."""
        try:
            plan = getattr(
                getattr(workspace, "subscription", None), "plan", None,
            )
            monthly = plan.features.get("ai_credits_monthly", 600) if plan else 600
            threshold = int(monthly * 0.20)

            now = timezone.now()

            if wallet.balance_total == 0 and not wallet.zero_balance_alert_sent_at:
                wallet.zero_balance_alert_sent_at = now
                wallet.save(update_fields=["zero_balance_alert_sent_at"])
                logger.info(
                    "ai.alert.zero_balance",
                    extra={"workspace_id": str(workspace.id)},
                )

            elif (
                wallet.balance_total <= threshold
                and not wallet.low_balance_alert_sent_at
            ):
                wallet.low_balance_alert_sent_at = now
                wallet.save(update_fields=["low_balance_alert_sent_at"])
                logger.info(
                    "ai.alert.low_balance",
                    extra={
                        "workspace_id": str(workspace.id),
                        "balance": wallet.balance_total,
                        "threshold": threshold,
                    },
                )
        except Exception:
            # Alerts must never break the main flow
            logger.exception("ai.alert.check_failed")
