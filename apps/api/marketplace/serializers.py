from rest_framework import serializers
from .models import SecurityModule, WorkspaceModule

class SecurityModuleSerializer(serializers.ModelSerializer):
    is_purchased = serializers.SerializerMethodField()

    class Meta:
        model = SecurityModule
        fields = [
            "id", "slug", "name", "description", "short_description",
            "price", "currency", "stripe_price_id",
            "icon", "unlocked_strategies", "config_schema",
            "is_purchased", "created_at"
        ]

    def get_is_purchased(self, obj) -> bool:
        request = self.context.get("request")
        if request and request.user:
            from users.models import UserRole
            if request.user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]:
                return True

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
