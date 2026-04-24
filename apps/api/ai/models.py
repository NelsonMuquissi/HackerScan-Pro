"""
HackScan Pro — AI Credit System Models.

Tables:
  - AIWallet             (per-workspace credit balances with 3-bucket system)
  - AITransaction        (every credit movement with full financial metrics)
  - CreditPackage        (purchasable credit bundles)
  - Achievement          (gamification milestones that award credits)
  - WorkspaceAchievement (junction: workspace ↔ achievement unlocks)
  - MonthlyCreditGrant   (idempotent monthly subscription credit grants)

Design principles:
  - balance_subscription expires monthly; balance_purchased never expires
  - Debit order: subscription → purchased → bonus
  - cost_usd / revenue_usd / margin_pct are INTERNAL ONLY — never exposed via API
  - All wallet mutations use SELECT FOR UPDATE for thread safety
"""
from decimal import Decimal
from django.db import models
from django.utils import timezone

from core.models import UUIDModel, TimestampedModel
from users.models import Workspace


# ─── AIWallet ────────────────────────────────────────────────────────────────


class AIWallet(UUIDModel, TimestampedModel):
    """
    Per-workspace AI credit wallet with three separate balance buckets.

    balance_subscription: granted monthly by plan, expires at period end.
    balance_purchased:    bought via credit packages, never expires.
    balance_bonus:        earned via achievements/referrals, never expires.
    """
    workspace = models.OneToOneField(
        Workspace,
        on_delete=models.CASCADE,
        related_name="ai_wallet",
    )

    # ── Balance buckets ──
    balance_subscription = models.IntegerField(
        default=0,
        help_text="Credits from monthly plan grant. Expire at period end.",
    )
    balance_purchased = models.IntegerField(
        default=0,
        help_text="Credits bought via packages. Never expire.",
    )
    balance_bonus = models.IntegerField(
        default=0,
        help_text="Credits from achievements/referrals. Never expire.",
    )

    # ── Lifetime metrics ──
    lifetime_credits_granted = models.IntegerField(default=0)
    lifetime_credits_used = models.IntegerField(default=0)
    lifetime_revenue_usd = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
    )

    # ── Auto-reload ──
    auto_reload_enabled = models.BooleanField(default=False)
    auto_reload_threshold = models.IntegerField(default=100)
    auto_reload_package = models.CharField(
        max_length=50, blank=True, default="",
        help_text="Slug of the CreditPackage to auto-buy.",
    )
    auto_reload_stripe_pm = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Stripe PaymentMethod ID for auto-reload.",
    )

    # ── Alert state ──
    low_balance_alert_sent_at = models.DateTimeField(null=True, blank=True)
    zero_balance_alert_sent_at = models.DateTimeField(null=True, blank=True)

    # ── Loyalty ──
    consecutive_months_active = models.IntegerField(default=0)
    rollover_credits = models.IntegerField(default=0)

    # ── Express mode ──
    express_mode_enabled = models.BooleanField(default=False)

    class Meta:
        db_table = "ai_wallets"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(balance_subscription__gte=0),
                name="ck_ai_wallet_sub_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(balance_purchased__gte=0),
                name="ck_ai_wallet_purch_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(balance_bonus__gte=0),
                name="ck_ai_wallet_bonus_gte_0",
            ),
        ]

    def __str__(self) -> str:
        return f"AIWallet<{self.workspace.slug} | {self.balance_total} credits>"

    @property
    def balance_total(self) -> int:
        return self.balance_subscription + self.balance_purchased + self.balance_bonus


# ─── AITransaction ───────────────────────────────────────────────────────────


class TransactionType(models.TextChoices):
    CREDIT = "credit", "Credit"
    DEBIT = "debit", "Debit"


class AITransaction(UUIDModel):
    """
    Immutable ledger entry for every credit movement.

    CREDIT actions: purchase, monthly_grant, bonus_achievement,
                    referral_reward, welcome_bonus, auto_reload,
                    rollover, refund, admin_grant
    DEBIT actions:  explain_finding, explain_finding_first_use,
                    generate_report_pdf, generate_report_executive,
                    ai_forecaster, attack_chains, remediation_code,
                    chat_message, compliance_report, express_surcharge
    """
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="ai_transactions",
    )
    user = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ai_transactions",
    )

    # ── Type & categorisation ──
    type = models.CharField(max_length=20, choices=TransactionType.choices)
    action = models.CharField(max_length=100, db_index=True)

    # ── Debit source breakdown (order: subscription → purchased → bonus) ──
    debit_from_subscription = models.IntegerField(default=0)
    debit_from_purchased = models.IntegerField(default=0)
    debit_from_bonus = models.IntegerField(default=0)

    # ── Values ──
    amount = models.IntegerField()
    balance_before = models.IntegerField()
    balance_after = models.IntegerField()

    # ── Execution mode ──
    mode = models.CharField(
        max_length=20, default="standard",
        choices=[("standard", "Standard"), ("express", "Express")],
    )
    mode_multiplier = models.DecimalField(
        max_digits=3, decimal_places=1, default=Decimal("1.0"),
    )

    # ── AI metrics ──
    tokens_input = models.IntegerField(null=True, blank=True)
    tokens_output = models.IntegerField(null=True, blank=True)
    model_used = models.CharField(max_length=100, blank=True, default="")

    # ── Financial (INTERNAL — never exposed to client) ──
    cost_usd = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True,
    )
    revenue_usd = models.DecimalField(
        max_digits=10, decimal_places=6, null=True, blank=True,
    )
    margin_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
    )

    # ── Cache ──
    was_cached = models.BooleanField(default=False)
    cache_hit_key = models.CharField(max_length=255, blank=True, default="")

    # ── Resource reference ──
    reference_type = models.CharField(max_length=100, blank=True, default="")
    reference_id = models.UUIDField(null=True, blank=True)

    # ── Stripe (for purchases) ──
    stripe_payment_intent_id = models.CharField(
        max_length=255, blank=True, default="",
    )
    stripe_charge_id = models.CharField(
        max_length=255, blank=True, default="",
    )

    # ── Extra metadata ──
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "ai_transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["workspace", "-created_at"],
                name="idx_aitx_workspace_date",
            ),
            models.Index(
                fields=["type", "action"],
                name="idx_aitx_type_action",
            ),
            models.Index(
                fields=["stripe_payment_intent_id"],
                name="idx_aitx_stripe",
                condition=models.Q(stripe_payment_intent_id__gt=""),
            ),
        ]

    def __str__(self) -> str:
        return f"AITx<{self.type}|{self.action}|{self.amount}>"


# ─── CreditPackage ───────────────────────────────────────────────────────────


class CreditPackage(UUIDModel, TimestampedModel):
    """
    Purchasable credit bundle. Seeded with 5 tiers:
    Micro $1.99 · Starter $5 · Growth $20 · Power $50 · Ultra $100
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)
    tagline = models.CharField(max_length=255, blank=True, default="")

    credits = models.IntegerField()
    bonus_credits = models.IntegerField(default=0)

    price_usd = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_price_id = models.CharField(max_length=255, blank=True, default="")

    # ── Presentation ──
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    badge_text = models.CharField(max_length=50, blank=True, default="")
    sort_order = models.IntegerField(default=0)

    # ── Anti-fraud ──
    max_per_workspace_per_month = models.IntegerField(default=5)

    class Meta:
        db_table = "credit_packages"
        ordering = ["sort_order"]

    def __str__(self) -> str:
        return f"CreditPackage<{self.name} | {self.total_credits} credits | ${self.price_usd}>"

    @property
    def total_credits(self) -> int:
        return self.credits + self.bonus_credits

    @property
    def price_per_credit(self) -> Decimal:
        total = self.total_credits
        if total == 0:
            return Decimal("0")
        return self.price_usd / Decimal(total)


# ─── Achievement ─────────────────────────────────────────────────────────────


class Achievement(UUIDModel):
    """
    Gamification milestone that awards bonus credits when unlocked.
    """
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=50, blank=True, default="")
    credits = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "achievements"
        ordering = ["slug"]

    def __str__(self) -> str:
        return f"Achievement<{self.slug} | {self.credits} credits>"


class WorkspaceAchievement(UUIDModel):
    """
    Tracks which achievements a workspace has unlocked.
    """
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="achievements",
    )
    achievement = models.ForeignKey(
        Achievement, on_delete=models.CASCADE, related_name="unlocks",
    )
    unlocked_at = models.DateTimeField(default=timezone.now)
    credits_awarded = models.IntegerField()

    class Meta:
        db_table = "workspace_achievements"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "achievement"],
                name="uq_workspace_achievement",
            ),
        ]

    def __str__(self) -> str:
        return f"Unlock<{self.workspace.slug}|{self.achievement.slug}>"


# ─── MonthlyCreditGrant ─────────────────────────────────────────────────────


class MonthlyCreditGrant(UUIDModel):
    """
    Audit trail for monthly plan credit grants.
    Enforces idempotency via unique(workspace, period_start).
    """
    workspace = models.ForeignKey(
        Workspace, on_delete=models.CASCADE, related_name="monthly_credit_grants",
    )
    subscription = models.ForeignKey(
        "billing.Subscription", on_delete=models.CASCADE,
        related_name="credit_grants",
    )
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    credits_granted = models.IntegerField()
    rollover_added = models.IntegerField(default=0)
    granted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "monthly_credit_grants"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "period_start"],
                name="uq_monthly_grant_workspace_period",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"MonthlyGrant<{self.workspace.slug} | "
            f"{self.credits_granted} credits | {self.period_start.date()}>"
        )
