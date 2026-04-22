from rest_framework import serializers
from .models import Report
from scans.serializers import ScanTargetSerializer

class ReportSerializer(serializers.ModelSerializer):
    target_name = serializers.CharField(source="scan.target.name", read_only=True)
    target_host = serializers.CharField(source="scan.target.host", read_only=True)
    scan_type = serializers.CharField(source="scan.scan_type", read_only=True)
    
    class Meta:
        model = Report
        fields = [
            "id",
            "scan",
            "target_name",
            "target_host",
            "scan_type",
            "status",
            "type",
            "format",
            "file_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "file_url", "created_at", "updated_at"]
