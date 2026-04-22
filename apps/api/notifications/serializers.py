from rest_framework import serializers
from .models import Notification, NotificationPreference

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "title",
            "message",
            "is_read",
            "data",
            "created_at"
        ]
        read_only_fields = ["id", "type", "title", "message", "data", "created_at"]

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "workspace",
            "channel",
            "config",
            "is_active",
            "notify_on_complete",
            "notify_on_failed"
        ]
        read_only_fields = ["id", "workspace", "channel"]
