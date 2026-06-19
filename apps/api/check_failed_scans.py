import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from scans.models import Scan

failed_scans = Scan.objects.filter(status="failed").order_by("-created_at")[:5]

print(f"Checking {failed_scans.count()} most recent failed scans:\n")

for scan in failed_scans:
    print(f"ID: {scan.id}")
    print(f"Target: {scan.target.host}")
    print(f"Status: {scan.status}")
    print(f"Error Message: {scan.error_message}")
    print("-" * 40)
