import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from scans.models import Scan, ScanStatus

print("--- Scan Status Report ---")
for status, label in ScanStatus.choices:
    count = Scan.objects.filter(status=status).count()
    print(f"{label}: {count}")

print("\n--- Recent Failed Scans ---")
for s in Scan.objects.filter(status=ScanStatus.FAILED).order_by('-created_at')[:5]:
    print(f"ID: {s.id} | Target: {s.target.host} | Error: {s.error_message[:100]}...")

print("\n--- Pending/Queued Scans ---")
for s in Scan.objects.filter(status__in=[ScanStatus.PENDING, ScanStatus.QUEUED]).order_by('-created_at')[:5]:
    print(f"ID: {s.id} | Status: {s.status} | Target: {s.target.host}")
