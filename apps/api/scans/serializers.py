"""Serializers for the scans app."""
from rest_framework import serializers
from .models import Finding, Scan, ScanPlugin, ScanStatus, ScanTarget, ScheduledScan


class ScanTargetSerializer(serializers.ModelSerializer):
    scan_count = serializers.SerializerMethodField()

    class Meta:
        model  = ScanTarget
        fields = [
            "id", "name", "host", "target_type", "description",
            "is_verified", "tags", "scan_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_verified", "scan_count", "created_at", "updated_at"]

    def get_scan_count(self, obj) -> int:
        return obj.scans.count()


class ScanCreateSerializer(serializers.Serializer):
    from .models import ScanType  # noqa: PLC0415

    target_id = serializers.UUIDField()
    scan_type = serializers.ChoiceField(
        choices=ScanType.choices,
        default=ScanType.QUICK,
    )
    config = serializers.DictField(default=dict, required=False)


class FindingSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Finding
        fields = [
            "id", "plugin_slug", "severity", "status", "title", "description",
            "remediation", "evidence", "cvss_score",
            "fingerprint", "is_false_positive", "first_seen_at", "last_seen_at",
            "resolved_at", "created_at", "ai_explanation", "ai_remediation",
        ]
        read_only_fields = fields


class ScheduledScanSerializer(serializers.ModelSerializer):
    target_host = serializers.CharField(source="target.host", read_only=True)
    target_name = serializers.CharField(source="target.name", read_only=True)

    class Meta:
        model = ScheduledScan
        fields = [
            "id", "target", "target_host", "target_name", "scan_type",
            "frequency", "is_active", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        # Set triggered_by to the current user
        validated_data["triggered_by"] = self.context["request"].user
        return super().create(validated_data)


class ScanListSerializer(serializers.ModelSerializer):
    target_host = serializers.CharField(source="target.host", read_only=True)
    duration    = serializers.FloatField(source="duration_seconds", read_only=True)

    class Meta:
        model  = Scan
        fields = [
            "id", "target_host", "status", "plugin_ids",
            "total_findings", "critical_count", "high_count",
            "medium_count", "low_count", "info_count",
            "started_at", "finished_at", "duration", "created_at",
        ]
        read_only_fields = fields


class ScanDetailSerializer(ScanListSerializer):
    findings = FindingSerializer(many=True, read_only=True)
    target   = ScanTargetSerializer(read_only=True)

    class Meta(ScanListSerializer.Meta):
        fields = ScanListSerializer.Meta.fields + ["findings", "target", "error_message", "config"]


class ScanPluginSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ScanPlugin
        fields = ["id", "slug", "name", "description", "is_active"]
        read_only_fields = fields
