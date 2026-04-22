from rest_framework import serializers
from .models import SecurityModule, WorkspaceModule

class SecurityModuleSerializer(serializers.ModelSerializer):
    is_purchased = serializers.SerializerMethodField()

    class Meta:
        model = SecurityModule
        fields = [
            "id", "slug", "name", "description", "category",
            "price_monthly", "price_yearly", "stripe_price_id",
            "icon", "badge", "unlocked_strategies", "is_purchased",
            "created_at"
        ]

    def get_is_purchased(self, obj) -> bool:
        workspace_id = self.context.get("workspace_id")
        if not workspace_id:
            return False
        return WorkspaceModule.objects.filter(
            workspace_id=workspace_id,
            module=obj,
            is_active=True
        ).exists()

class ModuleCheckoutSerializer(serializers.Serializer):
    success_url = serializers.URLField()
    cancel_url = serializers.URLField()
