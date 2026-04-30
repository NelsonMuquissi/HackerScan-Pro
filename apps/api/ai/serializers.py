"""
HackScan Pro — AI Credit API serializers.

CRITICAL: cost_usd, revenue_usd, margin_pct are NEVER serialized here.
"""
from rest_framework import serializers

from .models import (
    AITransaction,
    AIWallet,
    Achievement,
    CreditPackage,
    WorkspaceAchievement,
)


class AIWalletSerializer(serializers.ModelSerializer):
    """Public wallet view — balance breakdown only."""

    balance_total = serializers.IntegerField(read_only=True)
    is_unlimited = serializers.SerializerMethodField()

    class Meta:
        model = AIWallet
        fields = [
            "id",
            "workspace",
            "balance_subscription",
            "balance_purchased",
            "balance_bonus",
            "balance_total",
            "is_unlimited",
            "lifetime_credits_granted",
            "lifetime_credits_used",
            "auto_reload_enabled",
            "auto_reload_threshold",
            "auto_reload_package",
            "express_mode_enabled",
            "consecutive_months_active",
            "rollover_credits",
        ]
        read_only_fields = fields

    def get_is_unlimited(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user:
            return False
        
        from users.models import UserRole
        return request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]


class AITransactionSerializer(serializers.ModelSerializer):
    """
    Public transaction view.
    Explicitly EXCLUDES cost_usd, revenue_usd, margin_pct.
    """

    class Meta:
        model = AITransaction
        fields = [
            "id",
            "type",
            "action",
            "amount",
            "balance_before",
            "balance_after",
            "debit_from_subscription",
            "debit_from_purchased",
            "debit_from_bonus",
            "mode",
            "was_cached",
            "reference_type",
            "reference_id",
            "created_at",
        ]
        read_only_fields = fields


class CreditPackageSerializer(serializers.ModelSerializer):
    """Public package listing."""

    total_credits = serializers.IntegerField(read_only=True)
    price_per_credit = serializers.DecimalField(
        max_digits=10, decimal_places=6, read_only=True,
    )

    class Meta:
        model = CreditPackage
        fields = [
            "id",
            "name",
            "slug",
            "tagline",
            "credits",
            "bonus_credits",
            "total_credits",
            "price_usd",
            "price_per_credit",
            "is_featured",
            "badge_text",
            "sort_order",
        ]
        read_only_fields = fields


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ["id", "slug", "name", "description", "icon", "credits"]
        read_only_fields = fields


class WorkspaceAchievementSerializer(serializers.ModelSerializer):
    achievement = AchievementSerializer(read_only=True)

    class Meta:
        model = WorkspaceAchievement
        fields = ["id", "achievement", "unlocked_at", "credits_awarded"]
        read_only_fields = fields
