from rest_framework import serializers
from .models import Webhook

class WebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        fields = [
            'id', 'workspace', 'name', 'url', 'secret_token', 
            'events', 'is_active', 'last_triggered_at', 
            'last_status_code', 'created_at'
        ]
        read_only_fields = ['id', 'secret_token', 'last_triggered_at', 'last_status_code', 'created_at']

    def validate_events(self, value):
        valid_events = ["scan.completed", "scan.failed", "finding.new"]
        for event in value:
            if event not in valid_events:
                raise serializers.ValidationError(f"Invalid event: {event}")
        return value
