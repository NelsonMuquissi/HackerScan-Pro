import os
import django
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from scans.models import Scan, ScanStatus

stuck_scans = Scan.objects.filter(status=ScanStatus.RUNNING)

print(f"Found {stuck_scans.count()} scans in RUNNING state.")

for scan in stuck_scans:
    print(f"Cancelling scan {scan.id} (Target: {scan.target.host}, Started: {scan.started_at})")
    scan.status = ScanStatus.FAILED
    scan.error_message = "Scan stuck in RUNNING state for too long. Manually marked as FAILED."
    scan.finished_at = timezone.now()
    scan.save()

print("Done.")
