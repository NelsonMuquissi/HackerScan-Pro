import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from scans.models import Scan

failed_scans = Scan.objects.filter(status="failed").order_by("-created_at")[:10]

print(f"Found {len(failed_scans)} failed scans.\n")

for scan in failed_scans:
    print(f"--- Scan ID: {scan.id} ---")
    print(f"Target: {scan.target.host}")
    print(f"Type: {scan.scan_type}")
    print(f"Error:\n{scan.error_message}")
    print("-" * 50)
