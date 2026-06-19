from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import GlobalSetting
from .permissions import IsSuperAdmin
from rest_framework import serializers

class GlobalSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSetting
        fields = ["id", "key", "value", "description", "category", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

class GlobalSettingViewSet(viewsets.ModelViewSet):
    """
    Administrative interface for managing platform-wide settings.
    """
    queryset = GlobalSetting.objects.all().order_by("category", "key")
    serializer_class = GlobalSettingSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    lookup_field = "key"

    @action(detail=False, methods=["get"])
    def by_category(self, request):
        category = request.query_params.get("category", "general")
        settings = self.queryset.filter(category=category)
        serializer = self.get_serializer(settings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def batch_update(self, request):
        """
        Update multiple settings at once.
        Expects a list of {key: value} or [{key, value}]
        """
        data = request.data
        if not isinstance(data, list):
            return Response({"error": "Expected a list of settings"}, status=status.HTTP_400_BAD_REQUEST)
        
        results = []
        for item in data:
            key = item.get("key")
            value = item.get("value")
            if key:
                setting, created = GlobalSetting.objects.update_or_create(
                    key=key,
                    defaults={"value": value}
                )
                results.append(GlobalSettingSerializer(setting).data)
        
        return Response(results)
